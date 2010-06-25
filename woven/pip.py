#!/usr/bin/env python
import os,sys

#TODO Check these
from fabric.api import env, local, run, prompt, put,get, sudo
from fabric.context_managers import cd, hide
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project, upload_project
from fabric.contrib.console import confirm
from fabric.context_managers import settings

from woven.virtualenv import Virtualenv
from woven.utils import server_state, set_server_state


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

            