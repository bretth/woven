#!/usr/bin/env python
import os
from woven.ubuntu import install_packages, upgrade_ubuntu, setup_ufw, disable_root
from woven.ubuntu import uncomment_sources, restrict_ssh, upload_ssh_key, change_ssh_port, set_timezone

def setup_environ(settings=None):
    """
    Used in management commands or at the module level of a fabfile to
    integrate project django.conf settings into fabric, and set the local current
    working directory to the distribution root (where setup.py lives). 

    """
    #switch the working directory to the distribution root where setup.py is
    original_fabfile = env.fabfile
    env.fabfile = 'setup.py'
    local_working_dir = os.path.split(find_fabfile())[0]
    env.fabfile = original_fabfile
    os.chdir(local_working_dir)

    env.project_name = local('python setup.py --name').rstrip()
    env.project_version = project_version()
    env.project_fullname = env.project_name + '-' + env.project_version
    
    #We'll assume that if the settings aren't passed in we're running from a fabfile
    if not settings:
        sys.path.insert(0,local_working_dir)
        #First try a multi-site configuration
        #TODO - import multiple settings files for per-site settings
        try:
            project_settings = import_module(env.project_name+'settings.settings')
        except ImportError:
            project_settings = import_module(env.project_name+'.settings')
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
    env.user = project_settings.HOST_USER
    env.password = project_settings.HOST_PASSWORD
    
    #since port is not handled by fabric.main.normalize we'll do it ourselves
    host_list = []
    for host_string in env.all_hosts:
        if not ':' in host_string:
            host_string += ':%s'% str(project_settings.HOST_SSH_PORT)
        host_list.append(host_string)
        env.all_hosts = host_list
    
    #Now update the env with any settings that are not woven specific
    #but may be used by woven or fabric
    env.MEDIA_ROOT = project_settings.MEDIA_ROOT
    env.ADMIN_MEDIA_PREFIX = project_settings.ADMIN_MEDIA_PREFIX
    #static_root is from static_builder
    if not env.get('STATIC_ROOT'): env.STATIC_ROOT = env.MEDIA_ROOT
    #If sqlite is used we can manage the database on deployment
    env.DEFAULT_DATABASE_ENGINE = project_settings.DATABASES['default']['ENGINE']
    #Set the server /etc/timezone
    env.TIME_ZONE = project_settings.TIME_ZONE
    #Used to detect certain apps eg South, static_builder
    env.INSTALLED_APPS = project_settings.INSTALLED_APPS
    #noinput
    if not hasattr(env,'INTERACTIVE'): env.INTERACTIVE=True
    
    #The default domain - usually taken from a directory name
    if not env.get('DOMAINS'): env.DOMAINS = [root_domain()]
    
    #TODO - deployment_root is used for deployment but may be best set in the deploy script
    #since it uses hoststring context
    #if not env.get("deployment_root"): env.deployment_root = '/home/%s/%s'% (env.user,env.DOMAINS[0])    
    if not env.get('PIP_REQUIREMENTS'): env.PIP_REQUIREMENTS = ''

def setupserver(rollback=False):
    """
    Install a baseline host. Can be run multiple times
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
        install_packages()
        set_timezone()
        
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

