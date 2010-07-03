#!/usr/bin/env python
"""
Set up a Virtualenv environment and install packages/dependencies in the environment with pip
"""
import os, shutil
import tempfile
from  datetime import datetime

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
from woven.utils import project_fullname, project_name, project_version, active_version

class Virtualenv(object):
    """
    Simple virtualenv proxy and base class for subclasses that use a
    virtualenv environment
    """
    state = 'created_virtualenv_'
    def __init__(self, version=''):
        if not version:
            self.fullname = project_fullname()
            self.version = project_version()
        else:
            self.fullname = env.fullname = project_name()+'-'+version
            self.version = version

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
        self.pip_log = '/home/%s/.pip/'% env.user

        self.pip_files = env.PIP_REQUIREMENTS[:]
        self.pybundles = []

        if not self.pip_files:
            #Use any file starting with req and ending with .txt
            with settings(warn_only=True):
                p = local('ls req*.txt').rstrip().split('\n')
                if p[0]: self.pip_files += p
            #look for any pybundles that match the requirements eg requirements-0.1.pybundle
            for req in self.pip_files:
                
                bundle = req.replace('.txt','') +'-'+self.version+'.pybundle'

                if os.path.exists('dist/%s'% bundle):
                    #dist is the default dist-dir=DIR in distribute etc
                    self.pip_files.remove(req)
                    self.pip_files.append(bundle)
                    self.pybundles.append(bundle)
                    print self.pybundles
                    print self.pip_files

            
def pip_install_requirements(rollback=False):
    """
    Install on current installed virtualenv version from a [dist/project name-version].pybundles or pip ``req.txt``|``requirements.txt``
    or a env.pip_requirements list.
    
    By default it will look for a pybundle in the dist directory first then a requirements file.

    
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
        print env.host, 'PIP INSTALLING REQUIREMENTS:'
    #Remove any pre-existing pip-log from a previous failed installation
    if exists(p.pip_log):
        run('rm -rf '+p.pip_log)
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
    if p.pybundles or 'file://' in env.DJANGO_REQUIREMENT:
        s = tempfile.mkdtemp()
        env.woventempdirs = env.woventempdirs + [s]
        staging = os.path.join(s,'dist')
        os.mkdir(staging)
        if p.pybundles:
            for pfile in p.pybundles:
                shutil.copy('dist/'+pfile,staging)
        if 'file://' in env.DJANGO_REQUIREMENT:
            local_django = env.DJANGO_REQUIREMENT.replace('file://','')
            shutil.copy(local_django,staging)
        #Rsync the dist directory first 
        rsync_project(local_dir=staging,remote_dir=env.deployment_root,extra_opts=extra_opts,exclude=exclude,delete=False)

    #if no requirements file exists create one
    if not p.pip_files:
        f = open("requirements.txt","w+")
        f.write("#Set your project requirements here\n")
        f.write("#By default the current release of Django is installed automatically before any requirements\n\n")
        f.write("#A specific version of Django (as a pip install argument) can be set in settings DJANGO_REQUIREMENT\n")
        f.write("#For example to install the development version: DJANGO_REQUIREMENT='-e svn+http://code.djangoproject.com/svn/django/trunk/#egg=Django'")
        f.write("#To install your own local version: DJANGO_REQUIREMENT='file:///path/to/Django-1.2.1.tar.gz'")
        f.write("#Requirements files can be named in order of installation. Anything with req*.txt will be treated as a requirement file\n")
        f.write("#eg req1.txt requirements2.txt ...\n\n")
        f.write("woven\n")

        f.close()
        p.pip_files = ["requirements.txt"]
    #put any remaining files ie requirements files up
    for file in p.pip_files:
        if '.pybundle' not in file:
            put(file,p.dist+file)
    
    with cd(p.dist):
        print env.host, ' * installing',env.DJANGO_REQUIREMENT
        if 'file://' in env.DJANGO_REQUIREMENT:
            local_django = env.DJANGO_REQUIREMENT.replace('file://','')
            django_filename = os.path.split(local_django)[1]
            django_req = env.deployment_root+'dist/'+django_filename
        else:
            django_req = env.DJANGO_REQUIREMENT
        with settings(warn_only=True):    
            install = run('pip install %s -q --environment=%s --download-cache=%s --log=/home/%s/.pip/django_pip_log.txt'% (django_req,p.python_path,p.cache, env.user))
        for req in p.pip_files:
            with settings(warn_only=True):
                command = 'install'
                #if rollback: command = 'uninstall'
                #else: command = 'install'
                if env.verbosity:
                    print env.host, ' * installing',req
                if '.pybundle' in req and not rollback:
                    install = run('pip install %s -q --environment=%s --log=/home/%s/.pip/%s_pip_log.txt'% (req, p.python_path, env.user, req.replace('.pybundle','_pybundle')))
                    
                else:
                    #if rollback: install = run('pip uninstall -qy --environment=%s --requirement=%s'% (p.python_path,p.dist+req))
                    install = run('pip install -q --environment=%s --download-cache=%s --requirement=%s --log=/home/%s/.pip/%s_pip_log.txt'% (p.python_path,p.cache,p.dist+req, env.user,req.replace('.txt','')))

    if install.failed and not rollback:
        #TODO - just print this at the end... somehow instead of downloading
        print 'PIP errors on %s please review the pip log which will be downloaded to'% command
        tar_file = "/tmp/pip-log.%s.tar" % datetime.utcnow().strftime('%Y_%m_%d_%H-%M-%S')
        with cd('/home/%s/.pip/'% env.user):
            files = run("tar -czf %s ." % tar_file,env.user)
        get(tar_file,'./pip-logs.tar.gz')
        run('rm -f '+tar_file)
        return False
    else:
        if rollback: delete = True
        else: delete = False
        set_server_state('pip_installed_'+p.fullname,delete=delete)
        if env.verbosity:
            print env.host,'PIP %sED PACKAGES'% command.upper()
    if rollback: #finally for rollback and delete cache to be complete
        for req in p.pip_files:
            run('rm -f '+p.dist+req)
        run('rm -rf '+p.cache)
        ls = run('ls '+ p.dist).rstrip().split('\n')

        run('rm -rf '+p.dist)
        
    return True


    
        
        
    