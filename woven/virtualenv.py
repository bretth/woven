#!/usr/bin/env python
from glob import glob
import os, sys

from django import get_version
from django.template.loader import render_to_string

from fabric.state import env 
from fabric.operations import run, sudo
from fabric.context_managers import cd, settings
from fabric.contrib.files import exists

from woven.deployment import mkdirs, run_once_per_host_version, deploy_files
from woven.environment import deployment_root,set_server_state, server_state, State
from woven.webservers import _ls_sites, stop_webservices, start_webservices
from fabric.contrib.files import append

def active_version():
    """
    Determine the current active version on the server
    
    Just examine the which environment is symlinked
    """
    
    link = '/'.join([deployment_root(),'env',env.project_name])
    if not exists(link): return None
    active = os.path.split(run('ls -al '+link).split(' -> ')[1])[1]
    return active

def activate():
    """
    Activates the version or the current version if criteria is met
    """

    env_path = '/'.join([deployment_root(),'env',env.project_fullname])

    if not exists(env_path):
        print env.host,"ERROR: The version",env.project_version,"does not exist at"
        print env_path
        sys.exit(1)

    active = active_version()

    if env.patch or active <> env.project_fullname:
        stop_webservices()
        
    if not env.patch and active <> env.project_fullname:
        #TODO - DATA MIGRATION HERE
        if env.verbosity:
            print env.host, "ACTIVATING version", env_path
        #delete existing symlink
        ln_path = '/'.join([env.deployment_root,'env',env.project_name])
        run('rm -f '+ln_path)
        run('ln -s %s %s'% (env_path,ln_path))
        #create shortcuts for virtualenv activation in the home directory
        activate_env = '/'.join(['/home',env.user,'workon-'+env.project_name])
        if not exists(activate_env):
            run("touch "+activate_env)
            append('#!/bin/bash',activate_env)
            append("source "+ os.path.join(env.deployment_root,'env',env.project_name,'bin','activate'),
                   activate_env)
            append("cd "+ os.path.join(env.deployment_root,'env',env.project_name,'project',env.project_name),
                   activate_env)
            run("chmod +x "+activate_env)
        
        #activate sites
        #enabled_sites = _ls_sites('/etc/apache2/sites-enabled') + _ls_sites('/etc/nginx/sites-enabled')
        activate_sites = [''.join([d.replace('.','_'),'-',env.project_version,'.conf']) for d in env.DOMAINS]
        site_paths = ['/etc/apache2','/etc/nginx']
        
        #disable existing sites
        for path in site_paths:
            for site in _ls_sites('/'.join([path,'sites-enabled'])):
                if site not in activate_sites:
                    sudo("rm %s/sites-enabled/%s"% (path,site))
        
        #activate new sites
        for path in site_paths:
            for site in activate_sites:
                if not exists('/'.join([path,'sites-enabled',site])):
                    sudo("chmod 644 %s" % '/'.join([path,'sites-available',site]))
                    sudo("ln -s %s/sites-available/%s %s/sites-enabled/%s"% (path,site,path,site))
                    if env.verbosity:
                        print " * enabled", "%s/sites-enabled/%s"% (path,site)
  
        if env.verbosity:
            print env.host,env.project_fullname, "ACTIVATED"
    else:
        if env.verbosity and not env.patch:
            print env.project_fullname,"is the active version"
    if env.patch or active <> env.project_fullname:
        start_webservices()
        print
    return

@run_once_per_host_version
def mkvirtualenv():
    root = '/'.join([deployment_root(),'env'])
    path = '/'.join([root,env.project_fullname])
    dirs_created = []
    if env.verbosity:
        print env.host,'CREATING VIRTUALENV', path
    if not exists(root): dirs_created += mkdirs(root)
    with cd(root):
        run(' '.join(["virtualenv",env.project_fullname]))
    with cd(path):
        dirs_created += mkdirs('egg_cache')
        sudo('chown -R %s:www-data egg_cache'% env.user)
        sudo('chmod -R g+w egg_cache')
    
    #Create a state
    out = State(' '.join([env.host,'virtualenv',path,'created']))
    out.object = dirs_created + ['bin','lib','include']
    out.failed = False
    return out
        
def rmvirtualenv():
    """
    Remove the current or ``env.project_version`` environment and all content in it
    """
    path = '/'.join([deployment_root(),'env',env.project_fullname])
    if server_state('mkvirtualenv'):
        sudo(' '.join(['rm -rf',path]))
        set_server_state('mkvirtualenv',delete=True)
    #If there are no further remaining envs we'll delete the home directory to effectively teardown the project
    if not server_state('mkvirtualenv',prefix=True):
        sudo('rm -rf '+env.deployment_root)        

@run_once_per_host_version    
def pip_install_requirements():
    """
    Install on current installed virtualenv version from a [dist/project name-version].pybundles or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a pybundle in the dist directory first then a requirements file.

    
    The limitations of installing requirements are that you cannot point directly to packages
    in your local filesystem. In this case you would bundle instead.
    """
    if not server_state('mkvirtualenv'):
        print env.host,'Error: Cannot run pip_install_requirements. A virtualenv is not created for this version. Run mkvirtualenv first'
        return
    if env.verbosity:
        print env.host, 'PIP INSTALLING REQUIREMENTS:'
    
    #Remove any pre-existing pip-log from any previous failed installation
    pip_log_dir = '/'.join(['/home',env.user,'.pip'])
    if exists(pip_log_dir): run(' '.join(['rm -rf' ,pip_log_dir]))
    
    #determine what req files or bundle files we need to deploy
    if not env.PIP_REQUIREMENTS:
        req_files = {}.fromkeys(glob('req*'))
    else:
        req_files = {}.fromkeys(env.PIP_REQUIREMENTS)
    
    for key in req_files:
        bundle = ''.join([key.split('.')[0],'.pybundle'])
        if os.path.exists(os.path.join('dist',bundle)):
            req_files[key] = bundle

    #if no requirements file exists create one
    if not req_files:
        f = open("requirements.txt","w+")
        text = render_to_string('woven/requirements.txt')
        f.write(text)
        f.close()
        req_files["requirements.txt"]=''
        
    req_files_list = req_files.keys()
    req_files_list.sort()
        
    #determine the django version
    file_patterns =''
    if 'file://' in env.DJANGO_REQUIREMENT:
        django_req = os.path.split(env.DJANGO_REQUIREMENT.replace('file://',''))[1]
        file_patterns = ''.join([django_req])

    elif env.DJANGO_REQUIREMENT:
        django_req = env.DJANGO_REQUIREMENT
    else:
        django_version = get_version()
        svn_version = django_version.find('SVN')
        if svn_version > -1:
            django_version = django_version[svn_version+4:]
            django_req = ''.join(['-e svn+http://code.djangoproject.com/svn/django/trunk@',svn_version,'#egg=Django'])
        else:
            django_req = ''.join(['Django==',django_version])
    req_files[django_req]=None
    req_files_list.insert(0,django_req)
    
    #patterns for bundles
    if req_files: file_patterns = '|'.join([file_patterns,'req*.pybundle'])

    #create a pip cache & src directory
    cache = '/'.join([deployment_root(),'package-cache'])
    src = '/'.join([env.deployment_root,'src'])
    deployed = mkdirs(cache)
    deployed += mkdirs(src)
    #deploy bundles and any local copy of django
    local_dir = os.path.join(os.getcwd(),'dist')
    remote_dir = '/'.join([env.deployment_root,'env',env.project_fullname,'dist'])
    if file_patterns: deployed += deploy_files(local_dir, remote_dir, pattern=file_patterns)
    
    #deploy any requirement files
    deployed +=  deploy_files(os.getcwd(), remote_dir, pattern = 'req*') 
    
    #install in the env
    out = State(' '.join([env.host,'pip install requirements']))
    python_path = '/'.join([env.deployment_root,'env',env.project_fullname,'bin','python'])
    with settings(warn_only=True):
        with cd(remote_dir):
            for req in req_files_list:
                bundle = req_files[req]
                if bundle: req=bundle
                if env.verbosity:
                    print ' * installing',req
                if '.pybundle' in req.lower() or 'django' in req.lower():
                    install = run('pip install %s -q --environment=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (req, python_path, env.user, req.replace('.','_')))
                else:
                    install = run('pip install -q --environment=%s --src=%s --download-cache=%s --requirement=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (python_path,src,cache,req, env.user,req.replace('.','_')))

                if install.failed:
                    out.failed =True
                    out.stderr += ' '.join([env.host, "ERROR INSTALLING",req,'\n'])
                    
                    #fabric 1.0
                    if hasattr(install,'stderr'):
                        out.stderr = '\n'.join([out.stderr,install.stderr])
    
    out.object = deployed
              
    if install.failed:
        print out.stderr
        sys.exit(1)
    return out
