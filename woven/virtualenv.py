#!/usr/bin/env python
from glob import glob
import os, sys
import site

from django import get_version
from django.template.loader import render_to_string

from fabric.decorators import runs_once
from fabric.state import env 
from fabric.operations import run, sudo
from fabric.context_managers import cd, settings
from fabric.contrib.files import exists
from fabric.contrib.console import confirm

from woven.deployment import mkdirs, run_once_per_host_version, deploy_files
from woven.environment import deployment_root,set_server_state, server_state, State
from woven.webservers import _get_django_sites, _ls_sites, stop_webservers, start_webservers, domain_sites
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
    Activates the version specified in ``env.project_version`` if it is different
    from the current active version.
    
    An active version is just the version that is symlinked.
    """

    env_path = '/'.join([deployment_root(),'env',env.project_fullname])

    if not exists(env_path):
        print env.host,"ERROR: The version",env.project_version,"does not exist at"
        print env_path
        sys.exit(1)

    active = active_version()

    if env.patch or active <> env.project_fullname:
        stop_webservers()
        
    if not env.patch and active <> env.project_fullname:
        
        if env.verbosity:
            print env.host, "ACTIVATING version", env_path
        
        if not env.nomigration:
            sync_db()
        
        #south migration
        if 'south' in env.INSTALLED_APPS and not env.nomigration and not env.manualmigration:
            migration()
            
        if env.manualmigration or env.MANUAL_MIGRATION: manual_migration()
      
        #activate sites
        activate_sites = [''.join([d.replace('.','_'),'-',env.project_version,'.conf']) for d in domain_sites()]
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
        
        #delete existing symlink
        ln_path = '/'.join([deployment_root(),'env',env.project_name])
        run('rm -f '+ln_path)
        run('ln -s %s %s'% (env_path,ln_path))

  
        if env.verbosity:
            print env.host,env.project_fullname, "ACTIVATED"
    else:
        if env.verbosity and not env.patch:
            print env.project_fullname,"is the active version"

    if env.patch or active <> env.project_fullname:
        start_webservers()
        print
    return

@runs_once
def sync_db():
    """
    Runs the django syncdb command
    """
    with cd('/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])):
        venv = '/'.join([deployment_root(),'env',env.project_fullname,'bin','activate'])
        sites = _get_django_sites()
        site_ids = sites.keys()
        site_ids.sort()
        for site in site_ids:
            site_settings = '.'.join([env.project_package_name,'sitesettings',sites[site].replace('.','_')])
            site_settings_py = '.'.join([sites[site].replace('.','_'),'py'])
            if not exists(site_settings_py): continue
            if env.verbosity:
                print " * python manage.py syncdb --noinput --settings=%s"% site_settings
            output = run(' '.join(['source',venv,'&&',"./manage.py syncdb --noinput --settings=%s"% site_settings]))
            if env.verbosity:
                print output

@runs_once
def manual_migration():
    """
    Simple interactive function to pause the deployment.
    A manual migration can be done two different ways:
    Option 1: Enter y to exit the current deployment. When migration is completed run deploy again.
    Option 2: run the migration in a separate shell   
    """
    if env.INTERACTIVITY:
        print "A manual migration can be done two different ways:"
        print "Option 1: Enter y to exit the current deployment. When migration is completed run deploy again."
        print "Option 2: run the migration in a separate shell"
        exit = confirm("Enter y to exit or accept default to complete deployment and activate the new version",default=False)
    else:
        exit = True
    if exit:
        print "Login to your node and run 'workon %s'"% env.project_fullname 
        sys.exit(0)

@runs_once
def migration():
    """
    Integrate with south schema migration
    """

    #activate env        
    with cd('/'.join([deployment_root(),'env',env.project_fullname,'project',env.project_package_name,'sitesettings'])):
        #migrates all or specific env.migration
        venv = '/'.join([deployment_root(),'env',env.project_fullname,'bin','activate'])
        cmdpt1 = ' '.join(['source',venv,'&&'])
        
        sites = _get_django_sites()
        site_ids = sites.keys()
        site_ids.sort()
        for site in site_ids:
            site_settings = '.'.join([env.project_package_name,'sitesettings',sites[site].replace('.','_')])
            site_settings_py = '.'.join([sites[site].replace('.','_'),'py'])
            if not exists(site_settings_py): continue
            cmdpt2 = ' '.join(["python manage.py migrate",env.migration])
            if hasattr(env,"fakemigration"):
                cmdpt2 = ' '.join([cmdpt2,'--fake'])
            cmdpt2 = ''.join([cmdpt2,'--settings=',site_settings])
            if env.verbosity:
                print " *", cmdpt2
            output = run(' '.join([cmdpt1,cmdpt2]))
        if env.verbosity:
            print output
    return           

@run_once_per_host_version
def mkvirtualenv():
    """
    Create the virtualenv project environment
    """
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
        run(''.join(["echo 'cd ",path,'/','project','/',env.project_package_name,'/sitesettings',"' > bin/postactivate"]))
        sudo('chmod ugo+rwx bin/postactivate')

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
    link = '/'.join([deployment_root(),'env',env.project_name])
    if server_state('mkvirtualenv'):
        sudo(' '.join(['rm -rf',path]))
        sudo(' '.join(['rm -f',link]))
        sudo('rm -f /var/local/woven/*%s'% env.project_fullname)
        set_server_state('mkvirtualenv',delete=True)
      

@run_once_per_host_version    
def pip_install_requirements():
    """
    Install on current installed virtualenv version from a pip bundle [dist/project name-version].zip or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a zip bundle in the dist directory first then a requirements file.

    
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
        bundle = ''.join([key.split('.')[0],'.zip'])
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
    if req_files: file_patterns = '|'.join([file_patterns,'req*.zip'])

    #create a pip cache & src directory
    cache =  '/'.join(['/home',env.user,'.package-cache'])
    src = '/'.join([deployment_root(),'src'])
    deployed = mkdirs(cache)
    deployed += mkdirs(src)
    #deploy bundles and any local copy of django
    local_dir = os.path.join(os.getcwd(),'dist')
    remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'dist'])
    if os.path.exists(local_dir):  
        if file_patterns: deployed += deploy_files(local_dir, remote_dir, pattern=file_patterns)
    
    #deploy any requirement files
    deployed +=  deploy_files(os.getcwd(), remote_dir, pattern = 'req*') 
    
    #install in the env
    out = State(' '.join([env.host,'pip install requirements']))
    python_path = '/'.join([deployment_root(),'env',env.project_fullname,'bin','python'])
    with settings(warn_only=True):
        with cd(remote_dir):
            for req in req_files_list:
                bundle = req_files[req]
                if bundle: req=bundle
                if env.verbosity:
                    print ' * installing',req
                if 'django' in req.lower():
                    install = run('pip install %s -q --environment=%s --src=%s --download-cache=%s --log=/home/%s/.pip/django_pip_log.txt'%
                                  (req, python_path, src, cache, env.user))  

                elif '.zip' in req.lower():
                    install = run('pip install %s -q --environment=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (req, python_path, env.user, req.replace('.','_')))
                  
                else:
                    install = run('pip install -q --environment=%s --src=%s --download-cache=%s --requirement=%s --log=/home/%s/.pip/%s_pip_log.txt'%
                                  (python_path,src,cache,req, env.user,req.replace('.','_')))
                if install.failed:
                    out.failed =True
                    out.stderr += ' '.join([env.host, "ERROR INSTALLING",req,'\n'])
    
    out.object = deployed
              
    if out.failed:
        print out.stderr
        print "Review the pip install logs at %s/.pip and re-deploy"% deployment_root()
        sys.exit(1)
    return out
