#!/usr/bin/env python
"""
Anything related to deploying within a python virtual environment is in this module.

This includes pip install, deploy project & deploy media

"""
import os
import tempfile

from django.core.servers.basehttp import AdminMediaHandler
from fabric.state import env

#TODO check these
from fabric.api import env, local, run, prompt, get, put, sudo
from fabric.context_managers import cd, hide, settings
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project, upload_project
from fabric.contrib.console import confirm

#Required for a bug in 0.9
from fabric.version import get_version

from woven.utils import root_domain, server_state, set_server_state
from woven.utils import project_fullname, project_name, active_version

class Virtualenv(object):
    """
    Simple virtualenv proxy and base class for subclasses that use a
    virtualenv environment
    """
    state = 'created_virtualenv_'
    def __init__(self, version=''):
        if not version: self.fullname = project_fullname()
        else: self.fullname = env.fullname = project_name()+'-'+version

        env.deployment_root = '/home/%s/%s/'% (env.user,root_domain())
        self.root = env.deployment_root +'env' 
        self.path = '/'.join([self.root,self.fullname])
        self.python_path = '/'.join([self.path,'bin','python'])
        if server_state(self.state+self.fullname):self.installed = True
        else: self.installed = False

def mkvirtualenv(version=''):
    """
    Create the ``current version`` or specified ``version`` env on the node
    """
    v = Virtualenv(version)
    if v.installed:
        if env.verbosity:
            print env.host,'Warning: Virtualenv %s already installed. Skipping..'% v.fullname
        return False
    else:
        #TODO: We need the apache conf to use WSGIPythonHome /usr/local/pythonenv/BASELINE
        # to allow no_site = True
        # otherwise modwsgi will still get the system installed packages.
        # To do this install a no-site-packages virtualenv
        # and then use that as the system wide modwsgi baseline
        # probably not a high priority
        if env.verbosity:
            print env.host,'CREATING VIRTUALENV',v.path
        no_site = False
        run('mkdir -p '+v.root)
        with cd(v.root):
            if no_site:
                run("virtualenv --no-site-packages %s" % v.fullname)
            else:
                run("virtualenv %s" % v.fullname)

        # some installations require an egg-cache that is writeable
        # by the apache user - normally www-data
        with cd(v.path):
            if not exists('egg_cache'):
                run('mkdir egg_cache')
            sudo('chown -R %s:www-data egg_cache'% env.user)
            sudo('chmod -R g+w egg_cache')

        #Set the state to virtualenv created
        set_server_state('created_virtualenv_'+v.fullname)
        return True

def rmvirtualenv(version=''):
    """
    Remove the current or ``version`` env and all content in it
    """
    v = Virtualenv(version)
    if v.installed: #delete
        sudo('rm -rf '+v.path)
        set_server_state('created_virtualenv_'+v.fullname,delete=True)
    #If there are no further remaining envs we'll delete the home directory to effectively teardown the project
    if not server_state('created_virtualenv_',prefix=True):
        sudo('rm -rf '+env.deployment_root)

class Pip(Virtualenv):
    """
    Simple proxy for pip
    """
    state = 'pip_installed_'
    def __init__(self, version=''):
        #Since pip installation uses Virtualenv we reuse existing Virtualenv functionality
        super(Pip,self).__init__(version)
        #We will store any pip cached packages and pybundles here
        self.dist = env.deployment_root+'dist/'
        self.cache = env.deployment_root+'package-cache/'
        #Errors get stored here (from pip defaults)
        self.pip_log = '/home/%s/.pip/pip.log'% env.user
        self.pip_files = []
        self.pybundle = ''
        #Test for pybundle existance - this must always happen first
        #cwd = os.getcwd()
        if os.path.exists('dist/%s.pybundle'% self.fullname):
            #dist is the default dist-dir=DIR in distribute etc
            self.pip_files = ['%s.pybundle'% self.fullname]
            self.pybundle = '%s.pybundle'% self.fullname
        #Use any file starting with req and ending with .txt
        #Even if pybundles exist we still need requirements for uninstallation
        self.pip_files += local('ls req*.txt').rstrip().split('\n')
            
def pip_install_requirements(rollback=False):
    """
    Install on current installed virtualenv version from a [dist/project name-version].pybundle or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a pybundle in the dist directory first then a requirements file.

    Leaves an install pip-log.txt dropping in the project dir on error which we will pick up
    and download.
    
    The limitations of installing requirements are that you cannot point directly to packages
    in your local filesystem. In this case you would bundle instead.
    """

    p = Pip()
    if p.installed and not rollback:
        if env.verbosity:
            print env.host,"Pip requirements already installed. Skipping.."
        return False

    elif not p.installed and rollback:
        if env.verbosity:
            print env.host,'Pip requirements not installed. Skipping...'
        return
    #TODO - this is probably better handled in the Virtualenv init
    elif not server_state('created_virtualenv_'+p.fullname):
        print env.host,'Error: Cannot run pip_install_requirements. A virtualenv is not created for this version. Run mkvirtualenv first'
        return False
    if env.verbosity:
        print env.host, 'PIP INSTALLING REQUIREMENTS'
    #Remove any pre-existing pip-log from a previous failed installation
    if exists(p.pip_log):
        run('rm -f '+p.pip_log)
    #Uploade the req and pybundle files
    if not rollback: #create p.cache directory
        run('mkdir -p '+p.cache)
        run('mkdir -p '+p.dist)
    #Work around the rsync issue in 0.9
    fab_vers = int(get_version(form='short')[0])
    if fab_vers < 1: extra_opts = '--rsh="ssh -p%s"'% env.port
    else: extra_opts = ''
    exclude = ['.*']
    #Optimize network copy
    if p.pybundle:
        local('mkdir -p /tmp/dist')
        local('cp -f %s %s'% ('dist/'+p.pybundle,'/tmp/dist/%s.pybundle'% project_name()))
        #Rsync the dist directory first 
        rsync_project(local_dir='/tmp/dist',remote_dir=env.deployment_root,extra_opts=extra_opts,exclude=exclude,delete=False)
        run('cp -f %s %s'% (p.dist+project_name()+'.pybundle',p.dist+p.pybundle))   
    #put any remaining files ie requirements files up
    for file in p.pip_files:
        if '.pybundle' not in file:
            put(file,p.dist+file)
    with cd(p.path):
        for req in p.pip_files:
            with settings(warn_only=True):
                if rollback: command = 'uninstall'
                else: command = 'install'
                if req == p.pybundle and not rollback:
                    install = run('pip install %s -q --environment=%s'% (p.dist+p.pybundle, p.python_path))
                    break #do not install anything else once a bundle is installed
                elif req <> p.pybundle:
                    if rollback: install = run('pip uninstall -qy --environment=%s --requirement=%s'% (p.python_path,p.dist+req))
                    else: install = run('pip install -q --environment=%s --download-cache=%s --requirement=%s'% (p.python_path,p.cache,p.dist+req))

    if exists(p.pip_log) or install.failed and not rollback:
        print 'PIP errors on %s please review the pip-log.txt which will be downloaded to'% command
        print os.getcwd()
        get(p.pip_log,'./')
        return False
    else:
        if rollback: delete = True
        else: delete = False
        set_server_state('pip_installed_'+p.fullname,delete=delete)
        if env.verbosity:
            print env.host,'PIP %sED '% command.upper(),' '.join(p.pip_files)
    if rollback: #finally for rollback and delete cache to be complete
        for req in p.pip_files:
            run('rm -f '+p.dist+req)
        run('rm -rf '+p.cache)
        ls = run('ls '+ p.dist).rstrip().split('\n')
        #If all we're left with is the generic pybundle or nothing then delete
        if not ls[0] or ls[0]==project_name()+'.pybundle':
            run('rm -rf '+p.dist)
        
    return True

#DEPLOY

class Project(Virtualenv):
    """
    Base class for deploying your project
    """
    state = 'deployed_project_'
    def __init__(self,version=''):
        super(Project,self).__init__(version)
        self.deploy_type = self.__class__.__name__.lower()
        self.deploy_root = env.deployment_root+'/'.join(['env',self.fullname,self.deploy_type,''])
        #try to exclude a few common things in the project directory
        self.rsync_exclude = ['*.pyc','*.log','.*','/build','/dist','/media','/app*','/www','/public']
        self.versioned = True
        self.local_path = './'
        self.setting =''
        self.dest_path_postfix = ''

    
    def deploy(self,patch=False):
        """
        Deploy your project
        """
        if not self.local_path:
            if env.verbosity:
                print "Warning: No %s set in project settings. Skipping %s..."% (self.setting,self.deploy_type)
                return False
        if self.installed and not patch:
            if env.verbosity:
                print env.host,"Warning: %s version %s already deployed. Skipping..."% (self.deploy_type,self.fullname)
            return False
        elif not self.installed and not patch:
            run('mkdir -p '+self.deploy_root)
        elif not self.installed and patch:
            if env.verbosity:
                print env.host,"Warning: Cannot patch %s. This version %s does not exist. Skipping.."% (self.deploy_type,self.fullname)
            return False
        #bug in fabric 0.9 on rsync on alternate port fixed in 1.0
        fab_vers = int(get_version(form='short')[0])
        if fab_vers < 1:
            extra_opts = '--rsh="ssh -p%s"'% env.port

        #to save a bit of network usage if there is an existing version we will copy that first
        if self.versioned:
            av = active_version()
            
            if av and not patch:
                delete=True
                av_root = self.deploy_root.replace(self.fullname,av)
                dest_root = self.deploy_root.replace(self.deploy_type+'/','')
                run('cp -R %s %s'% (av_root,dest_root))
            elif patch:
                delete=False
            else:
                delete=True
        else: delete = False
        #a dest_path_postfix is a /url/postfix/ from a django media setting
        #we need to create the full postfix directory on top of the deploy_root (eg STATIC_ROOT+ADMIN_MEDIA_PREFIX)
        if self.dest_path_postfix:
            last_postfix = self.dest_path_postfix.split('/')[-2] #since -1 will be trailing slash and thus empty
            remote_dir = self.deploy_root[:-1]+self.dest_path_postfix
            run('mkdir -p '+remote_dir)
            remote_dir = remote_dir.replace('/%s/'% last_postfix,'')
            tdir = tempfile.mkdtemp()
            local('mkdir -p %s/%s'% (tdir,last_postfix))
            local('cp -fR %s/* %s/%s'% (self.local_path,tdir,last_postfix))
            self.local_path = '%s/%s'% (tdir,last_postfix)
            
        else:
            remote_dir = self.deploy_root
        rsync_project(local_dir=self.local_path,remote_dir=remote_dir,
                      extra_opts=extra_opts,exclude=self.rsync_exclude,delete=delete)
        #delete orphaned .pyc - specific to projects
        if self.deploy_type == 'project':
            run("find %s -name '*.pyc' -delete"% self.deploy_root)

        set_server_state(self.state+self.fullname)
        if env.verbosity:
            print env.host,"DEPLOYED %s %s"% (self.deploy_type,self.fullname)
        return True
    
    def delete(self):
        #walk backwards up the tree
        if active_version <> self.fullname:
            run('rm -rf '+self.deploy_root)
        #if nothing left in the specific env
        ls = run('ls '+ self.path).rstrip().split('\n')
        if not ls[0]: run('rm -rf '+ self.path)
        #if no envs left
        ls = run('ls '+ self.root).rstrip().split('\n')
        if not ls[0]: run('rm -rf '+ env.deployment_root)
        set_server_state(self.state+self.fullname,delete=True)

     
def deploy_project(version='',patch=False):
    """
    Wrapper function for Project that also splits out the functionality related but
    not specific to projects, such as database.
    """
    p = Project(version)
    #Create an sqlite database directory if necessary
    if env.DEFAULT_DATABASE_ENGINE == 'django.db.backends.sqlite3' and not patch:
        db_dir = os.path.join(env.deployment_root,'database')
        if not exists(db_dir):
            run("mkdir -p %s"% db_dir)
            sudo("chown %s:www-data %s"% (env.user,db_dir))
            sudo("chmod ug+w %s"% db_dir)
    return p.deploy(patch)

class StaticMedia(Project):
    """
    A media specific class for deploying versioned application/project media per site
    
    In the simple use case, if django.contrib.admin is enabled then it will upload and
    version the default admin media.

    For more advanced use cases it is recommended you use django-staticfiles app to
    build your media including admin into a STATIC_ROOT folder locally
    
    """
    state = 'deployed_staticmedia_'
    def __init__(self, version=''):
        super(StaticMedia,self).__init__(version)
        self.rsync_exclude = ['*.pyc','*.log','.*']
        self.setting = 'STATIC_ROOT'
        
        if 'django.contrib.admin' in env.INSTALLED_APPS and not env.STATIC_ROOT:

            admin = AdminMediaHandler('DummyApp')
            self.local_path = admin.media_dir
            self.dest_path_postfix = env.ADMIN_MEDIA_PREFIX
        else:
            self.local_path = env.STATIC_ROOT
           
        
def deploy_static_media(version='',patch=False):
    """
    Wrapper for StaticMedia class
    """

    s = StaticMedia(version)
    s.deploy(patch)

class Public(StaticMedia):
    """
    A media specific class for deploying MEDIA_ROOT
    strips any prefix http:// and creates a directory with the domain name and trailing path
    
    MEDIA_ROOT is not versioned
    
    """
    state = 'deployed_public_'
    def __init__(self, version=''):
        super(Public,self).__init__(version)
        self.deploy_root = env.deployment_root+'/'.join([self.deploy_type,''])
        self.setting = 'MEDIA_ROOT'
        self.local_path = env.MEDIA_ROOT
        self.dest_path_postfix = env.MEDIA_URL.replace('http:/','')
        self.versioned = False
       
def deploy_public(version='',patch=False):
    """
    Wrapper for Public class
    """
    s = Public(version)
    s.deploy(patch)
        
    
    
        
        
    