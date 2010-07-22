#!/usr/bin/env python
import json, os, string, sys
from contextlib import nested

from django.utils.importlib import import_module


from fabric.context_managers import _setenv, settings
from fabric.contrib.files import exists
from fabric.decorators import runs_once
from fabric.main import find_fabfile
from fabric.operations import local, sudo, prompt
from fabric.state import _AttributeDict, env

woven_env = _AttributeDict({
'HOSTS':[], #optional - a list of host strings to setup on as per Fabric
'DOMAINS':[], #optional a list of domains that will be deployed on the host. The first is the primary domain
'ROLEDEFS':{'staging':['']}, #optional as per fabric. Staging will be used in deployment
'HOST_SSH_PORT':10022, #optional - the ssh port to be setup
'HOST_USER':'', #optional - can be used in place of defining it elsewhere (ie host_string)
'HOST_PASSWORD':'',#optional

#The first setup task is usually disabling the default root account and changing the ssh port.
#If root is already disabled and the port changed. we assume the host_string user is already created and has sudo permissions

'ROOT_DISABLED': False, #optional - also means the port has been changed to a new port.
'ROOT_PASSWORD':'', #optional - blank by default
'DEFAULT_SSH_PORT':22, #optional - The default ssh port, prior to woven changing it. Defaults to 22
'UFW_DISABLED':False, #optional - If some alternative firewall is already pre-installed
'UFW_RULES':['allow 80/tcp','allow 443/tcp'], #optional - the default firewall rules (note ssh is always allowed)

#The default ubuntu packages that are setup. It is NOT recommended you change these:
'HOST_BASE_PACKAGES':[
        'unattended-upgrades', #base
        'subversion','git-core','mercurial','bzr', #version control
        'gcc','build-essential', 'python-dev', 'python-setuptools', #build
        'apache2','libapache2-mod-wsgi','nginx', #webservers
        'python-paramiko','fabric',
        'python-imaging', #pil
        'python-psycopg2','python-mysqldb','python-pysqlite2'], #default database drivers

#Put any additional packages here 
'HOST_EXTRA_PACKAGES':[], #optional - additional ubuntu packages as required

    
#Virtualenv/Pip
'PIP_REQUIREMENTS':[], # a list of pip requirement and or pybundle files to use for installation
'DJANGO_REQUIREMENT':'Django',#A pip requirements string for the version of Django to install

#Application media
'STATIC_URL':'', #optional
'STATIC_ROOT':'', #optional

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

@runs_once
def _root_domain():
    """
    Deduce the root domain name, usually a 'naked' domain but not necessarily. 
    """
    if not hasattr(env,'root_domain'):
        cwd = os.getcwd().split(os.sep)
        domain = ''
        #if the first env.host has a domain name then we'll use that
        #since there are no top level domains that have numbers in them we can test env.host
        if env.host[-1] in string.ascii_letters:
            domain_parts = env.host.split('.')
            length = len(domain_parts)
            if length==2:
                #assumes .com .net etc so we want the full hostname for the domain
                domain = env.host
            elif length==3 and len(domain_parts[-1])==2:
                #assume country tld so we want the full hostname for domain
                domain = env.host
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

def deployment_root():
    #determine domain for deployment commands/funcs
    if not env.DOMAINS:
        env.DOMAINS = [_root_domain()]
    else: env.root_domain = env.DOMAINS[0]
    if not env.deployment_root:
        if env.root_domain: env.deployment_root = '/'.join(['/home',env.user,env.root_domain])
        else: env.deployment_root = '/'.join(['/home',env.user])
    return env.deployment_root

def set_env(settings=None, setup_dir=''):
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

    #project env variables for deployment
    env.project_name = project_name()
    env.project_full_version = local('python setup.py --version').rstrip()
    env.project_version = _parse_project_version(env.project_full_version)
    env.project_fullname = '-'.join([env.project_name,env.project_version])
    env.patch = False

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
    

    env.deployment_root = ''


def patch_project():
    return env.patch

def project_name():
    """
    Get the project name from the setup.py
    """
    project_name = local('python setup.py --name').rstrip()
    return project_name

def project_fullname(version=''):
    project_fullname = project_name() + '-' + _parse_project_version(version)
    return project_fullname


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
            sudo("echo '%s' > /var/local/woven/%s"% (json.dumps(object),state_name))
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
    state.content = None
    state.failed = True
    if not prefix and exists('/var/local/woven/%s'% full_name, use_sudo=True):
        content = sudo('cat /var/local/woven/%s'% full_name).strip()
        state.name = full_name
        state.failed = False
        if content:
            state.object = json.loads(content)
    elif prefix:
        with settings(warn_only=True):
            current_state = sudo('ls /var/local/woven/%s*'% name)
        if not current_state.failed:
            state.name = name
            state.failed = False
    return state
    
