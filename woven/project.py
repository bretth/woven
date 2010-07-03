#!/usr/bin/env python
"""
Anything related to deploying your project modules, media, and data
"""
import os, shutil, sys
import tempfile

from django.core.servers.basehttp import AdminMediaHandler
from django.template import Context, Template

from fabric.state import env

#TODO check these
from fabric.api import env, local, run, prompt, get, put, sudo
from fabric.context_managers import cd, hide, settings
from fabric.decorators import runs_once
from fabric.contrib.files import exists, comment
from fabric.contrib.project import rsync_project, upload_project
from fabric.contrib.console import confirm

#Required for a bug in 0.9
from fabric.version import get_version

from woven.utils import root_domain, server_state, set_server_state
from woven.utils import project_fullname, project_name, active_version, upload_template

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
        self.rsync_exclude = ['*.pyc','*.log','.*','/build','/dist','/media','/app*','/www','/public','/templates']
        
        self.versioned = True
        self.local_path = './'
        self.local_settings_dir = os.path.join('./',project_name(),'sitesettings')
        
        #the name of a settings.py setting
        self.setting =''
        self.dest_path_postfix = ''
        if not env.DOMAINS: env.DOMAINS = [root_domain()]
    
    @runs_once
    def make_local_sitesettings(self,overwrite=False):
        if not os.path.exists(self.local_settings_dir) or overwrite:
            if overwrite:
                shutil.rmtree(self.local_settings_dir,ignore_errors=True)
            os.mkdir(self.local_settings_dir)
            f = open(self.local_settings_dir+'/__init__.py',"w")
            f.close()
        site_id = 0
        for domain in env.DOMAINS:
            site_id+=1
            settings_file_path = os.path.join(self.local_settings_dir,domain.replace('.','_')+'.py')
            if not os.path.exists(settings_file_path):
                output ="""#Import global project settings
from %s.settings import *

#Override global settings with site/host local settings
#template tags will be substituted on project deployment
#Customize and add any other local site settings as required

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/home/{{ user }}/{{ root_domain }}/database/{{ project_name }}.db', # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    }
}

#Amend this if required
SITE_ID = %s

#Normally you won't need to amend these settings
MEDIA_ROOT = '/home/{{ user }}/{{ root_domain }}/public/'
STATIC_ROOT = '/home/{{ user }}/{{ root_domain }}/env/{{ project_fullname }}/static/'
TEMPLATE_DIRS = ('/home/{{ user }}/{{ root_domain }}/env/{{ project_fullname }}/templates/',
                '/home/{{ user }}/{{ root_domain }}/env/{{ project_fullname }}/templates/{{ domain }}',)
"""% (project_name(), site_id)
                f = open(settings_file_path,"w+")
                f.writelines(output)
                f.close()
 
        return
    
    
    def stage_local_files(self):
        #a dest_path_postfix is a /url/postfix/ from a django media setting
        #we need to create the full postfix directory on top of the deploy_root (eg STATIC_ROOT+ADMIN_MEDIA_PREFIX)
        #so locally we create a tmp staging directory to rsync from
        staging_dir = '%s_staging_dir'% self.deploy_type
        #ensure this is run only once per deploy_type
        if hasattr(env,staging_dir):
            return env[staging_dir]

        env[staging_dir] = s = tempfile.mkdtemp()

        #for cleanup later
        env.woventempdirs = env.woventempdirs + [s]
        shutil.copytree(self.local_path,os.path.join(s,self.last_postfix))
        #render settings files and replace
        if self.deploy_type == 'project':
            context = {
                'user':env.user,
                'project_name':project_name(),
                'project_fullname':project_fullname(),
                'root_domain':root_domain(),
                
            }
            for d in env.DOMAINS:
                context['domain']=d
                template_file = d.replace('.','_') + '.py'
                template_path = os.path.join(s,'project',project_name(),'sitesettings',template_file)
                f = open(template_path,"r")
                t = f.read()
                f.close()
                t = Template(t)
                rendered = t.render(Context(context))
                f = open(template_path,"w+")
                f.write(rendered)
                f.close()
        return s

    
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
            #Webserver must be able to write into the public directory in the case of fileuploads
            #TODO - Make this optional??
            if self.deploy_type == 'public':
                sudo("chown -R www-data:sudo %s" % self.deploy_root[:-1]) #strip trailing /
                sudo("chmod -R ug+w %s"% self.deploy_root[:-1])
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
        
        if self.dest_path_postfix:
            self.last_postfix = self.dest_path_postfix.split('/')[-2] #since -1 will be trailing slash and thus empty
            postfix = self.dest_path_postfix.replace(self.last_postfix+'/','')
            remote_dir = self.deploy_root[:-1]+postfix
            run('mkdir -p '+remote_dir)

        else:
            self.last_postfix = self.deploy_type
            remote_dir = env.deployment_root+'/'.join(['env',self.fullname])
        
        staging_dir = self.stage_local_files()

        rsync_project(local_dir=os.path.join(staging_dir,self.last_postfix),remote_dir=remote_dir,
                      extra_opts=extra_opts,exclude=self.rsync_exclude,delete=delete)

        
        #delete orphaned .pyc - specific to projects & remove 'woven' from installed apps
        if self.deploy_type == 'project':
            run("find %s -name '*.pyc' -delete"% self.deploy_root)
            
            

        set_server_state(self.state+self.fullname)
        if env.verbosity:
            if patch: print env.host,"PATCHED %s "% (self.deploy_type)
            else: print env.host,"DEPLOYED %s "% (self.deploy_type)
            
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

     
def deploy_project(version='',patch=False, overwrite=False):
    """
    Wrapper function for Project that also splits out the functionality related but
    not specific to projects, such as database.
    """
    p = Project(version)
    #all domains on all hosts
    p.make_local_sitesettings(overwrite)
    return p.deploy(patch)

class Templates(Project):
    """
    Deploys your global TEMPLATE_DIR and any subdirectories 
        
    """
    state = 'deployed_templates_'
    def __init__(self, template_dir, version='' ):
        super(Templates,self).__init__(version)
        self.rsync_exclude = ['*.pyc','*.log','.*']
           
            
        self.local_path = template_dir

def deploy_templates(version='',patch=False):
    """
    Wrapper around the Templates class
    """
    if not hasattr(env, 'project_template_dir'):
        #the normal pattern would mean the shortest path is the main one.
        #its probably the last listed
        length = 1000   
        
        for dir in env.TEMPLATE_DIRS:
            if dir:
                len_dir = len(dir)
                if len_dir < length:
                    length = len_dir
                    env.project_template_dir = dir
    
    if hasattr(env,'project_template_dir'):
        s = Templates(env.project_template_dir,version)

        s.deploy(patch)
    return
    
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
        
        #if app media is not handled by django-staticfiles we can install admin media by default
        if 'django.contrib.admin' in env.INSTALLED_APPS and not env.STATIC_ROOT:
            if env.MEDIA_URL in env.ADMIN_MEDIA_PREFIX:
                print "ERROR: Your ADMIN_MEDIA_PREFIX must not be on the same path as your MEDIA_URL"
                print "for example you cannot use MEDIA_URL = /media/ and ADMIN_MEDIA_PREFIX = /media/admin/"
                sys.exit(1)
            env.STATIC_URL = env.ADMIN_MEDIA_PREFIX    
            admin = AdminMediaHandler('DummyApp')
            self.local_path = admin.media_dir
            self.dest_path_postfix = env.ADMIN_MEDIA_PREFIX
        else:
            if env.MEDIA_URL in env.STATIC_URL:
                print "ERROR: Your STATIC_URL must not be on the same path as your MEDIA_URL"
                print "for example you cannot use MEDIA_URL = /media/ and STATIC_URL = /media/static/"
                sys.exit(1)        
        
def deploy_static(version='',patch=False):
    """
    Wrapper for StaticMedia class
    """
    if 'http' in env.STATIC_URL:
        if env.verbosity:
            print env.host,"Static media to be hosted externally at %s Skipping..."% env.STATIC_URL
        return

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
    if 'http' in env.MEDIA_URL:
        if env.verbosity:
            print env.host,"Public media to be hosted externally at %s Skipping..."% env.MEDIA_URL
        return
    s = Public(version)
    s.deploy(patch)
    return

@runs_once
def deploy_db(rollback=False):
    """
    Deploy a sqlite database from development
    """
    env.deployment_root = '/home/%s/%s/'% (env.user,root_domain())
    db_name = env.deployment_root + '/'.join(['database',project_name()+'.db'])
    
    if not rollback:
        db_dir = env.deployment_root+'database'
        if env.DEFAULT_DATABASE_ENGINE=='django.db.backends.sqlite3' and not exists(db_name):

            if env.verbosity:
                print env.host,"DEPLOYING DEFAULT SQLITE DATABASE to",db_name
            if not os.path.exists(env.DEFAULT_DATABASE_NAME) or not env.DEFAULT_DATABASE_NAME:
                print "ERROR: the database does not exist. Run python manage.py syncdb to create your database first."
                sys.exit(1)
            run('mkdir -p '+db_dir)
            put(env.DEFAULT_DATABASE_NAME,db_name)
            sudo("chown -R %s:www-data %s"% (env.user,db_dir))
            sudo("chmod -R ug+w "+db_dir)
    elif rollback and env.DEFAULT_DATABASE_ENGINE=='django.db.backends.sqlite3':
        if env.INTERACTIVE:
            delete = confirm('DELETE the database on the host?',default=False)
            if delete:
                run('rm -f '+db_name)
    
    return

   
        
   
