#!/usr/bin/env python
"""
Anything related to deploying a python virtual environment is in this module.

"""

from fabric.state import env

#TODO check these
from fabric.api import env, local, run, prompt, put, sudo
from fabric.context_managers import cd, hide
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
        env.deployment_root = env.get(env.deployment_root,'/home/%s/%s/'% (env.user,root_domain()))
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



