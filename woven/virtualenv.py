#!/usr/bin/env python
"""
Set up a Virtualenv environment and install packages/dependencies in the environment with pip
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

    
        
        
    