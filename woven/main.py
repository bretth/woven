#!/usr/bin/env python
import os,sys

from django.utils.importlib import import_module

from fabric.api import env, local, run, cd, sudo, settings
from fabric.main import find_fabfile
from fabric.contrib.files import append, exists

from woven.ubuntu import install_packages, upgrade_ubuntu, setup_ufw, disable_root
from woven.ubuntu import uncomment_sources, restrict_ssh, upload_ssh_key, change_ssh_port, set_timezone
from woven.utils import project_name, project_version, root_domain, rmtmpdirs
from woven.virtualenv import mkvirtualenv, pip_install_requirements
from woven.project import deploy_static, deploy_public, deploy_project, deploy_db, deploy_templates
from woven.webservers import deploy_wsgi, deploy_webservers, start_webservices, stop_webservices
from woven.global_settings import woven_env

def _ls_sites(path):
    """
    List only sites in the env.DOMAINS to ensure we co-exist with other projects
    """
    with cd(path):
        sites = run('ls').split('\n')
        doms = env.DOMAINS
        dom_sites = []
        for s in sites:
            ds = s.split('-')[0]
            ds = ds.replace('_','.')
            if ds in doms and s not in dom_sites:
                dom_sites.append(s)
    return dom_sites

def _activate_sites(path, filenames):
    enabled_sites = _ls_sites(path)            
    for site in enabled_sites:
        if env.verbosity:
            print env.host,'Disabling', site
        if site not in filenames:
            sudo("rm %s/%s"% (path,site))
        
        sudo("chmod 644 %s" % site)
        if not exists('/etc/apache2/sites-enabled'+ filename):
            sudo("ln -s %s%s %s%s"% (self.deploy_root,filename,self.enabled_path,filename))

def active_version():
    """
    Determine the current active version on the server
    
    Just examine the which environment is symlinked
    """
    link = '/'.join([env.deployment_root,'env',env.project_name])
    if not exists(link): return None
    active = os.path.split(run('ls -al '+link).split(' -> ')[1])[1]
    return active

def activate():
    """
    Activates the version or the current version if criteria is met
    """
    active = active_version()

    if env.patch or active <> env.project_fullname:
        stop_webservices()
        
    if not env.patch and active <> env.project_fullname:
        #TODO - DATA MIGRATION HERE

        #delete existing symlink
        run('rm -f '+os.path.join(env.deployment_root,'env',env.project_name))
        run('ln -s %s %s'% (os.path.join(env.deployment_root,'env',env.project_fullname),
                            os.path.join(env.deployment_root,'env',env.project_name))
           )
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
            print env.host,env.project_fullname, "ACTIVATED"
    else:
        if env.verbosity and not env.patch:
            print env.project_fullname,"is the active version"
    if env.patch or active <> env.project_fullname:
        start_webservices()
        print
    

def deploy():
    """
    deploy a versioned project on the host

    """
    deploy_funcs = [deploy_project,deploy_templates, deploy_static, deploy_public,  deploy_webservers, deploy_wsgi]
    if not env.patch:
        deploy_funcs = [deploy_db,mkvirtualenv,pip_install_requirements] + deploy_funcs
    for func in deploy_funcs: func()
 
def patch():
    """
    Patch the current version. Does not install packages or delete files
    """
    with settings(patch=True):
        deploy()
        activate()
    

def setup_environ(settings=None, setup_dir=''):
    """
    Used in management commands or at the module level of a fabfile to
    integrate woven project django.conf settings into fabric, and set the local current
    working directory to the distribution root (where setup.py lives).
    
    ``settings`` is your optional django.conf imported settings.
    
    ``setup_dir`` is an optional path to the directory containing setup.py
    This would be used in instances where setup.py was not above the cwd

    """
    #TODO tighter integration with fabric 1.0 fabric.contrib.django
    
    #switch the working directory to the distribution root where setup.py is
    original_fabfile = env.fabfile
    env.fabfile = 'setup.py'
    if setup_dir:
        fabfile_path = os.path.join(setup_dir,'setup.py')
    else:
        fabfile_path = find_fabfile()
    if not fabfile_path:
        print 'Error: You must have a setup.py file above your project directory'
        sys.exit(1)
        
    local_working_dir = os.path.split(fabfile_path)[0]
    env.fabfile = original_fabfile
    os.chdir(local_working_dir)

    #We'll assume that if the settings aren't passed in we're running from a fabfile
    if not settings:
        sys.path.insert(0,local_working_dir)
        #First try a multi-site configuration
        #TODO - import multiple settings files for per-site settings
        try:
            project_settings = import_module(project_name()+'settings.settings')
        except ImportError:
            project_settings = import_module(project_name()+'.settings')
    else:
        project_settings = settings
    
    #If the settings are optionally stored in a dictionary in the settings file
    #to prevent namespace clashes
    if hasattr(project_settings,'WOVEN'):
        local_settings = project_settings.WOVEN
        woven_env.update(local_settings)
    else: #alternatively if the settings are at module level as per normal usage
        local_settings = dir(project_settings)

        for setting in local_settings:
            if setting.isupper() and hasattr(woven_env,setting):
                s = getattr(project_settings,setting,'')
                woven_env[setting] = s
    
    #upate the fabric env with all the woven settings
    env.update(woven_env)
    
    #set any user/password defaults if they are not supplied
    #Fabric would get the user from the options by default as the system user
    #We will overwrite that
    if woven_env.HOST_USER:
        env.user = woven_env.HOST_USER
    env.password = woven_env.HOST_PASSWORD
    
    #set the hosts
    if not env.hosts: env.hosts = woven_env.HOSTS
    
    #since port is not handled by fabric.main.normalize we'll do it ourselves
    host_list = []
    for host_string in env.hosts:
        #print 'host_string',woven_env.HOST_SSH_PORT
        if not ':' in host_string:
            host_string += ':%s'% str(woven_env.HOST_SSH_PORT)
        #not sure that this is necessary but it seems clearer to make full
        #hoststrings with the correct user
        if not '@' in host_string:
            host_string = env.user + '@' + host_string
        host_list.append(host_string)
        env.hosts = host_list
    
    #Now update the env with any settings that are not woven specific
    #but may be used by woven or fabric
    env.MEDIA_ROOT = project_settings.MEDIA_ROOT
    env.MEDIA_URL = project_settings.MEDIA_URL
    env.ADMIN_MEDIA_PREFIX = project_settings.ADMIN_MEDIA_PREFIX
    env.TEMPLATE_DIRS = project_settings.TEMPLATE_DIRS
   
    #If sqlite is used we can manage the database on deployment
    env.DEFAULT_DATABASE_ENGINE = project_settings.DATABASES['default']['ENGINE']
    env.DEFAULT_DATABASE_NAME = project_settings.DATABASES['default']['NAME']
    
    #Set the server /etc/timezone
    env.TIME_ZONE = project_settings.TIME_ZONE
    #Used to detect certain apps eg South, static_builder
    env.INSTALLED_APPS = project_settings.INSTALLED_APPS
    #noinput
    if not hasattr(env,'INTERACTIVE'): env.INTERACTIVE=True
    
    #placeholder for staging directories to cleanup after deployment
    env.woventempdirs = []
    


def setupnode(rollback=False, overwrite=False):
    """
    Install a baseline host. Can be run multiple times
    
    rollback=True to teardown the installation
    """
    
    #either fabric or manage.py will setup the roles & hosts env
    #setup_environ handles passing all the project settings into env
    #and any woven.global_settings not already defined.
    if not rollback:
        port_changed = change_ssh_port()
        #We need to assume that if the port does not get changed that
        #it has already been done and thus we do not need to disable root
        if port_changed and not env.ROOT_DISABLED:
            disable_root()
        upload_ssh_key()
        restrict_ssh()
        uncomment_sources()
        upgrade_ubuntu()
        setup_ufw()
        install_packages(overwrite=overwrite)
        set_timezone()
        
        if env.verbosity:
            print env.host,"SETUPNODE complete"
            print "Note: setupnode can be re-run at anytime."
            print "You can now ssh %s@%s -p%s into your host"% (env.user,env.host,env.port)
        
    else:
        #rollback in reverse order of installation
        #The only things we don't rollback are the updates
        set_timezone(rollback)
        install_packages(rollback)
        setup_ufw(rollback)
        uncomment_sources(rollback)
        restrict_ssh(rollback)
        upload_ssh_key(rollback)
        if not env.ROOT_DISABLED:
            disable_root(rollback)
            change_ssh_port(rollback)

