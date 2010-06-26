#!/usr/bin/env python
"""
Anything related to deploying within a python virtual environment is in this module.

"""
import os
from fabric.state import env

#TODO check these
from fabric.api import env, local, run, prompt, put, sudo
from fabric.context_managers import cd, hide, settings
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project, upload_project
from fabric.contrib.console import confirm

from woven.utils import root_domain, server_state, set_server_state

class Virtualenv(object):
    """
    Simple virtualenv proxy and base class for subclasses that use a
    virtualenv environment
    """
    state = 'created_virtualenv_'
    def __init__(self, version=''):
        if not version: self.version = env.project_fullname
        else: self.version = env.project_name+'-'+version
        env.deployment_root = '/home/%s/%s/'% (env.user,root_domain())
        self.root = env.deployment_root +'env' 
        self.path = '/'.join([self.root,self.version])
        self.python_path = '/'.join([self.path,'bin','python'])
        if server_state(self.state+self.version):self.installed = True
        else: self.installed = False

def mkvirtualenv(version=''):
    """
    Create the ``current version`` or specified ``version`` env on the node
    """
    v = Virtualenv(version)
    if v.installed:
        if env.verbosity:
            print env.host,'Warning: Virtualenv %s already installed. Skipping..'% v.version
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
                run("virtualenv --no-site-packages %s" % v.version)
            else:
                run("virtualenv %s" % v.version)

        # some installations require an egg-cache that is writeable
        # by the apache user - normally www-data
        with cd(v.path):
            if not exists('egg_cache'):
                run('mkdir egg_cache')
            sudo('chown -R %s:www-data egg_cache'% env.user)
            sudo('chmod -R g+w egg_cache')

        #Set the state to virtualenv created
        set_server_state('created_virtualenv_'+v.version)
        return True

def rmvirtualenv(version=''):
    """
    Remove the current or ``version`` env and all content in it
    """
    v = Virtualenv(version)
    if v.installed: #delete
        sudo('rm -rf '+v.path)
        set_server_state('created_virtualenv_'+v.version,delete=True)
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
        self.cache = env.deployment_root+'dist'
        #Errors get stored here (from pip defaults)
        self.pip_log = '/home/%s/.pip/pip.log'% env.user
        #Test for pybundle existance
        if os.path.exists('%s.pybundle'% env.project_name) and not env.PIP_REQUIREMENTS:
            self.pip_files = ['%s.pybundle'% env.project_name]
        elif os.path.exists('dist/%s.pybundle'% env.project_name) and not env.PIP_REQUIREMENTS:
            self.pip_files = ['dist/%s.pybundle'% env.project_name]
        elif not env.PIP_REQUIREMENTS:
            #Use any file starting with req and ending with .txt
            self.pip_files = local('ls req*.txt').rstrip().split('\n')
        else:
            self.pip_files = env.PIP_REQUIREMENTS
        self.dest_files = {}
        for file in self.pip_files:
            dest_file = file
            if '.pybundle' in file:
                self.pybundle = dest_file = self.cache + '/' + file.split('/')[-1]
            else:
                dest_file = self.path + '/' + file
            self.dest_files[file]=dest_file    
            
def pip_install_requirements(rollback=False):
    """
    Install on current installed virtualenv version from a [project name].pybundle or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a pybundle in the setup.py directory or dist directory first then a requirements file.
    Alternatively a pybundle path can be defined in settings.PIP_REQUIREMENTS
    
    e.g. PIP_REQUIREMENTS = ['req1.txt','requirements.txt']
    
    or
    
    PIP_REQUIREMENTS =  ['somebundle.pybundle',...]
    
    Leaves an install pip-log.txt dropping in the project dir on error which we will pick up
    and download.
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
    elif not server_state('created_virtualenv_'+p.version):
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
    for file in p.dest_files:
        put(file,p.dest_files[file])
            
    with cd(p.path):
        for req in p.pip_files:
            with settings(warn_only=True):
                if rollback: command = 'uninstall'
                else: command = 'install' 
                if '.pybundle' in req:
                    install = run('pip %s %s -q --environment=%s'% (command,p.pybundle, p.python_path))
                else:
                    if rollback: install = run('pip uninstall -qy --environment=%s --requirement=%s'% (p.python_path,req))
                    else: install = run('pip install -q --environment=%s --download-cache=%s --requirement=%s'% (p.python_path,p.cache,req))

    if exists(p.pip_log) or install.failed and not rollback:
        print 'PIP errors on %s please review the pip-log.txt which will be downloaded to'% command
        print os.getcwd()
        get(p.pip_log,'./')
        return False
    else:
        if rollback: delete = True
        else: delete = False
        set_server_state('pip_installed_'+p.version,delete=delete)
        if env.verbosity:
            print env.host,'PIP %sED '% command.upper(),' '.join(p.pip_files)
    if rollback: #finally for rollback delete cache to be complete
        run('rm -rf '+p.cache)
        
    return True

#DEPLOY

class Deploy(Virtualenv):
    """
    Base class for deploying your project
    """
    def __init__(self,version=''):
        super(Deploy,self).__init__(version)


