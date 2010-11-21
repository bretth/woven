#!/usr/bin/env python
import json, os, string, sys, tempfile
from contextlib import nested
from distutils.core import run_setup

from django.utils.importlib import import_module

from fabric.context_managers import _setenv, settings, cd
from fabric.contrib.files import exists, comment, contains, sed, append
from fabric.decorators import runs_once, hosts
from fabric.main import find_fabfile
from fabric.network import normalize
from fabric.operations import local, run, sudo, prompt, get, put
from fabric.state import _AttributeDict, env, output
        

woven_env = _AttributeDict({
'HOSTS':[], #optional - a list of host strings to setup on as per Fabric
'ROLEDEFS':{}, #optional as per fabric. eg {'staging':['woven@example.com']}
'HOST_SSH_PORT':10022, #optional - the ssh port to be setup
'HOST_USER':'', #optional - can be used in place of defining it elsewhere (ie host_string)
'HOST_PASSWORD':'',#optional
'SSH_KEY_FILENAME':'',#optional - as per fabric, a path to a key to use in place your local .ssh key 

#The first setup task is usually disabling the default root account and changing the ssh port.
'ROOT_USER':'root', #optional - mostly the default administrative account is root
'DISABLE_ROOT': False, #optional - disable the default administrative account
'ROOT_PASSWORD':'', #optional - blank by default
'DEFAULT_SSH_PORT':22, #optional - The default ssh port, prior to woven changing it. Defaults to 22
'DISABLE_SSH_PASSWORD': False, #optional - setting this to true will disable password login and use ssh keys only.
'ENABLE_UFW':True, #optional - If some alternative firewall is already pre-installed
#optional - the default firewall rules (note ssh is always allowed)
'UFW_RULES':['allow woven_project'], 
'ROLE_UFW_RULES':{},
    
#The default ubuntu packages that are setup. It is NOT recommended you change these:
'HOST_BASE_PACKAGES':['ufw', #firewall
        'subversion','git-core','mercurial','bzr', #version control
        'gcc','build-essential', 'python-dev', 'python-setuptools', #build
        'apache2','libapache2-mod-wsgi','nginx', #webservers
        'python-paramiko','fabric',
        'python-imaging', #pil
        'python-psycopg2','python-mysqldb','python-pysqlite2'], #default database drivers

'HOST_EXTRA_PACKAGES':[], #optional - additional ubuntu packages as required

'ROLE_PACKAGES':{},#define ROLEDEFS packages instead of using HOST_BASE_PACKAGES + HOST_EXTRA_PACKAGES
    
#Virtualenv/Pip
'DEPLOYMENT_ROOT':'',
'PROJECT_APPS_PATH':'',#a relative path from the project package directory for any local apps
'PIP_REQUIREMENTS':[], #a list of pip requirement and or pybundle files to use for installation
'DJANGO_REQUIREMENT':'',#A pip requirements string for the version of Django to install

#Application media
'STATIC_URL':'', #optional
'STATIC_ROOT':'', #optional

#Database migrations
'MANUAL_MIGRATION':False, #optional Manage database migrations manually

})

def _parse_project_version(version=''):
    """
    Returns the significant part of the version excluding the build
       
    The final forms returned can be
    
    major.minor
    major.minor stage (spaces will be replaced with '-')
    major.minor.stage
    major.minor-stage
    major.minorstage (eg 1.0rc1)
    major.minor.maintenance
    major.minor.maintenance-stage
    major.minor.maintenancestage
    
    Anything beyond the maintenance or stage whichever is last is ignored 
    """
    
    def mm_version(vers):
        stage = ''
        stage_sep = ''
        finalvers = ''
        if not vers.isdigit():
            for num,char in enumerate(vers):
                if char.isdigit():
                    finalvers += str(char)
                elif char.isalpha():
                    stage = vers[num:]
                    break
                elif char in [' ','-']: #sep
                    #We will strip spaces to avoid needing to 'quote' paths
                    stage_sep = '-'
                    stage = vers[num+1:]
                    break
        else:
            finalvers = vers
        #remove any final build numbers
        if ' ' in stage:
            stage = stage.split(' ')[0]
        elif '-' in stage:
            stage = stage.split('-')[0]
        return (finalvers,stage,stage_sep)
        
    v = version.split('.')
    if len(v)==1: return v[0]
    major = v[0]
    minor = v[1]
    maint = ''
    stage = ''
    if len(v)>2 and v[2]<>'0': #(1.0.0 == 1.0)
        maint = v[2]
    if len(v)>3 and v[3][0].isalpha():
        stage = v[3]
        project_version = '.'.join([major,minor,maint,stage])
    else:
        #Detect stage in minor
        minor,stage_minor,stage_minor_sep = mm_version(minor)
        if maint: #may be maint = ''
            maint, stage_maint, stage_maint_sep = mm_version(maint)
        else:
            stage_maint = ''; stage_maint_sep = ''
        if stage_minor:
            stage = stage_minor
            stage_sep = stage_minor_sep
        elif stage_maint:
            stage = stage_maint
            stage_sep = stage_maint_sep
        finalvers = [major,minor]
        if maint: finalvers.append(maint)
        finalvers = '.'.join(finalvers)
        if stage:
            finalvers = stage_sep.join([finalvers,stage])
        project_version = finalvers
   
    return project_version

def _root_domain():
    """
    Deduce the root domain name - usually a 'naked' domain.
    
    This only needs to be done prior to the first deployment
    """

    if not hasattr(env,'root_domain'):
        cwd = os.getcwd().split(os.sep)
        domain = ''
        #if the first env.host has a domain name then we'll use that
        #since there are no top level domains that have numbers in them we can test env.host

        username, host, port = normalize(env.hosts[0])
        if host[-1] in string.ascii_letters:
            domain_parts = env.host.split('.')
            length = len(domain_parts)
            if length==2:
                #assumes .com .net etc so we want the full hostname for the domain
                domain = host
            elif length==3 and len(domain_parts[-1])==2:
                #assume country tld so we want the full hostname for domain
                domain = host
            elif length >=3:
                #assume the first part is the hostname of the machine
                domain = '.'.join(domain[1:])
        #we'll just pick the first directory in the path which has a period.
        else:
            for d in cwd:
                if '.' in d: 
                    domain = d
        if not domain and env.INTERACTIVE:
            domain = prompt('Enter the root domain for this project ',default='example.com')
        else:
            domain = 'example.com'
        env.root_domain = domain
    return env.root_domain

def check_settings():
    """
    Validate the users settings conf prior to deploy
    """
    valid=True
    if not env.MEDIA_ROOT or not env.MEDIA_URL:
        print "MEDIA ERROR: You must define a MEDIA_ROOT & MEDIA_URL in your settings.py"
        print "even if plan to deploy your media separately to your project"
        valid = False
    if not env.TEMPLATE_DIRS:
        print "TEMPLATES_DIRS ERROR: You must define a TEMPLATES_DIRS in your settings.py"
        valid=False
    if env.DEFAULT_DATABASE_ENGINE in ['django.db.backends.','django.db.backends.dummy']:
        print "DATABASE SETTINGS ERROR: The default database engine has not been defined in your settings.py file"
        print "At a minimum you must define an sqlite3 database for woven to deploy,"
        print "or define a database backend is managed outside of woven."    
        valid=False
    if not valid: sys.exit(1)

def disable_virtualenvwrapper():
    """
    Hack to workaround an issue with virtualenvwrapper logging caused by Fabric sudo
    
    Can also add --noprofile to env.shell
    """
    profile_path = '/'.join([deployment_root(),'.profile'])

    sed(profile_path,'source /usr/local/bin/virtualenvwrapper.sh','')

def enable_virtualenvwrapper():
    profile_path = '/'.join([deployment_root(),'.profile'])
    append('source /usr/local/bin/virtualenvwrapper.sh',profile_path)
    

def deployment_root():
    """
    deployment root varies per host based on the user
    
    It can be overridden by the DEPLOYMENT_ROOT setting

    """
    if not env.DEPLOYMENT_ROOT: return '/'.join(['/home',env.user])
    else: return env.DEPLOYMENT_ROOT

def get_project_version():
    return env.project_version

def set_env(settings=None, setup_dir=''):
    """
    Used in management commands or at the module level of a fabfile to
    integrate woven project django.conf settings into fabric, and set the local current
    working directory to the distribution root (where setup.py lives).
    
    ``settings`` is your django settings module to pass in
    if you want to call this from a fabric script.
    
    ``setup_dir`` is an optional path to the directory containing setup.py
    This would be used in instances where setup.py was not above the cwd
    
    This function is used to set the environment for all hosts
   
    """

    #switch the working directory to the distribution root where setup.py is
    original_fabfile = env.fabfile
    env.fabfile = 'setup.py'
    if setup_dir:
        fabfile_path = os.path.join(setup_dir,'setup.py')
    else:
        fabfile_path = find_fabfile()
    if not fabfile_path:
        print 'Error: You must create a setup.py file in your distribution'
        sys.exit(1)
        
    local_working_dir = os.path.split(fabfile_path)[0]
    env.fabfile = original_fabfile
    os.chdir(local_working_dir)
    
    setup = run_setup('setup.py',stop_after="init")

    if setup.get_name() == 'UNKNOWN' or setup.get_version()=='0.0.0' or not setup.packages:
        print "ERROR: You must define a minimum of name, version and packages in your setup.py"
        sys.exit(1)
    
    #project env variables for deployment
    env.project_name = setup.get_name() #project_name()
    env.project_full_version = setup.get_version()#local('python setup.py --version').rstrip()
    env.project_version = _parse_project_version(env.project_full_version)
    env.project_fullname = '-'.join([env.project_name,env.project_version])
    env.project_package_name = setup.packages[0]
    env.patch = False

    #django settings are passed in by the command
    #We'll assume that if the settings aren't passed in we're running from a fabfile
    if not settings:
        sys.path.insert(0,local_working_dir)
        
        #import global settings
        project_settings = import_module(env.project_name+'.settings')
    else:

        project_settings = settings
    
    #overwrite with main sitesettings module
    #just for MEDIA_URL, ADMIN_MEDIA_PREFIX, and STATIC_URL
    #if this settings file exists
    try:
        site_settings = import_module('.'.join([env.project_name,'sitesettings.settings']))
        project_settings.MEDIA_URL = site_settings.MEDIA_URL
        project_settings.ADMIN_MEDIA_PREFIX = site_settings.ADMIN_MEDIA_PREFIX
        if hasattr(site_settings,'STATIC_URL'):
            project_settings.STATIC_URL = site_settings.STATIC_URL
        else:
            project_settings.STATIC_URL = project_settings.ADMIN_MEDIA_PREFIX
    except ImportError:
        pass

    #update woven_env from project_settings    
    local_settings = dir(project_settings)
    #only get settings that woven uses
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
    if not env.roledefs: env.roledefs = woven_env.ROLEDEFS
    
    #since port is not handled by fabric.main.normalize we'll do it ourselves
    host_list = []
    if 'hosts' in env and isinstance(env['hosts'], list):
        for host_string in env.hosts:
            if not ':' in host_string:
                host_string += ':%s'% str(woven_env.HOST_SSH_PORT)
            #not sure that this is necessary but it seems clearer to make full
            #hoststrings with the correct user
            if not '@' in host_string:
                host_string = env.user + '@' + host_string
            host_list.append(host_string)
            env.hosts = host_list
    
    #Now update the env with any settings that are not defined by woven but may
    #be used by woven or fabric
    env.MEDIA_ROOT = project_settings.MEDIA_ROOT
    env.MEDIA_URL = project_settings.MEDIA_URL
    env.ADMIN_MEDIA_PREFIX = project_settings.ADMIN_MEDIA_PREFIX
    if not env.STATIC_URL: env.STATIC_URL = project_settings.ADMIN_MEDIA_PREFIX
    env.TEMPLATE_DIRS = project_settings.TEMPLATE_DIRS
   
    #If sqlite is used we can manage the database on deployment
    env.DEFAULT_DATABASE_ENGINE = project_settings.DATABASES['default']['ENGINE']
    env.DEFAULT_DATABASE_NAME = project_settings.DATABASES['default']['NAME']
    
    #Set the server /etc/timezone
    env.TIME_ZONE = project_settings.TIME_ZONE
    #Used to detect certain apps eg South, static_builder
    env.INSTALLED_APPS = project_settings.INSTALLED_APPS
    
    #SSH key
    if env.SSH_KEY_FILENAME: env.KEY_FILENAME = env.SSH_KEY_FILENAME
    else: env.KEY_FILENAME = ''
    
    #noinput
    if not hasattr(env,'INTERACTIVE'): env.INTERACTIVE=True
    if not hasattr(env,'verbosity'): env.verbosity=1
    
    #South integration defaults
    env.nomigration = False
    env.manualmigration = False
    env.migration = ''
    
    env.root_disabled = False
    
    #Sites
    env.sites = {}
    env.shell = '/bin/bash --noprofile -l -c'
    #output.debug = True
    
def patch_project():
    return env.patch

def project_version(full_version):
    """
    project_version context manager
    """

    project_full_version=full_version
    v = _parse_project_version(full_version)
    name = project_name()
    project_fullname = '-'.join([name,v])

    return _setenv(project_full_version=project_full_version, project_version=v,project_name=name,project_fullname=project_fullname)

class State(str):
    """
    State class - similar in principle and use to the _AttributeString in Fabric.
    
    It may be used to store stdout stderr etc.

    State has an object attribute to store objects
    for storage on the host using the set_server_state function and
    retrieve it using server_state.

    """
    def __init__(self,name,object=None):
        self.name = name
        self.object = object
        self.failed = False
        self.stderr = ''
        self.stdout = ''
    def __repr__(self):
        return str(self.name)
    def __str__(self):
        return str(self.name)
    def __bool__(self):
        return not self.failed
    def __len__(self):
        if self.failed: return 0
        else: return 1
    def __eq__(self, other):
        return self.name == other
    def __cmp__(self,other):
        return self.name == other
    def __ne__(self,other):
        return str(self.name) <> other

def set_server_state(name,object=None,delete=False):
    """
    Sets a simple 'state' on the server by creating a file
    with the desired state's name and storing ``content`` as json strings if supplied
    
    returns the filename used to store state   
    """
    if not hasattr(env,'project_name'): env.project_name = ''
    if not hasattr(env,'project_version'): env.project_version = ''
    state_name = '-'.join([name,env.project_name,env.project_version])
    with settings(warn_only=True):
        #Test for os state
        if not exists('/var/local/woven', use_sudo=True):
            sudo('mkdir /var/local/woven')
    if not delete:
        sudo('touch /var/local/woven/%s'% state_name)
        if object:
            fd, file_path = tempfile.mkstemp()
            f = os.fdopen(fd,'w')
            f.write(json.dumps(object))
            f.close()
            put(file_path,'/tmp/%s'% state_name)
            os.remove(file_path)
            sudo('cp /tmp/%s /var/local/woven/%s'% (state_name,state_name))
    else:
        sudo('rm -f /var/local/woven/%s'% state_name)
    return state_name

def server_state(name, prefix=False):
    """
    If the server state exists return parsed json as a python object or True if
    no content exists.
    
    If prefix returns True if any files exist with ls name*
    """
    if not hasattr(env,'project_name'): env.project_name = ''
    if not hasattr(env,'project_version'): env.project_version = ''
    full_name = '-'.join([name,env.project_name,env.project_version])
    state = State(full_name)
    state_path = '/var/local/woven/%s'% full_name
    state.content = None
    state.failed = True
    if not prefix and exists(state_path, use_sudo=True):
        content = int(sudo('ls -s %s'% state_path).split()[0]) #get size
        state.name = full_name
        state.failed = False
        if content:
            fd, file_path = tempfile.mkstemp()
            os.close(fd)
            get(state_path,file_path)
            with open(file_path, "r") as f:
                content = f.read()
                state.object = json.loads(content)
    elif prefix:
        with settings(warn_only=True):
            current_state = sudo('ls /var/local/woven/%s*'% name)
        if not current_state.failed:
            state.name = name
            state.failed = False
    return state
    
