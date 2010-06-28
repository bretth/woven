#!/usr/bin/env python
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

from woven.virtualenv import Virtualenv


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
        if self.installed and not patch and self.versioned:
            if env.verbosity:
                print env.host,"Warning: %s version %s already deployed. Skipping..."% (self.deploy_type,self.fullname)
            return False
        elif not self.installed and not patch:
            run('mkdir -p '+self.deploy_root)
        elif not self.installed and patch and self.versioned:
            if env.verbosity:
                print env.host,"Warning: Cannot patch %s. This version %s does not exist. Skipping.."% (self.deploy_type,self.fullname)
            return False
        l = local('ls '+self.local_path).rstrip()
        if not l:
            if env.verbosity:
                print "Warning: Theres are no files to deploy for %s. Skipping.."% self.deploy_type
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

class Static(Project):
    """
    A media specific class for deploying versioned application/project media per site
    
    In the simple use case, if django.contrib.admin is enabled then it will upload and
    version the default admin media.

    For more advanced use cases it is recommended you use django-staticfiles app to
    build your media including admin into a STATIC_ROOT folder locally
    
    """
    state = 'deployed_static_'
    def __init__(self, version=''):
        super(Static,self).__init__(version)
        self.rsync_exclude = ['*.pyc','*.log','.*']
        self.setting = 'STATIC_ROOT'
        
        if 'django.contrib.admin' in env.INSTALLED_APPS and not env.STATIC_ROOT:

            admin = AdminMediaHandler('DummyApp')
            self.local_path = admin.media_dir
            self.dest_path_postfix = env.ADMIN_MEDIA_PREFIX
        else:
            self.local_path = env.STATIC_ROOT
           
        
def deploy_static(version='',patch=False):
    """
    Wrapper for StaticMedia class
    """

    s = Static(version)
    s.deploy(patch)

class Public(Static):
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
        self.local_path = env.MEDIA_ROOT[:-1]
        self.dest_path_postfix = env.MEDIA_URL.replace('http:/','')
        self.versioned = False

    def delete(self):
        #if no envs
        if not exists(self.root):
            run('rm -rf '+ env.deployment_root)
            set_server_state(self.state+self.fullname,delete=True)
       
def deploy_public(version='',patch=False):
    """
    Wrapper for Public class
    """
    s = Public(version)
    s.deploy(patch)
        
   
