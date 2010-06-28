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
from woven.utils import upload_template

from woven.project import Project

class WSGI(Project):
    """
    Deploy a modwsgi file per domain
    """
    
    state = 'deployed_wsgi_'
    def __init__(self,version=''):
        super(WSGI,self).__init__(version)
        self.setting =''
        self.dest_path_postfix = ''
    
    def deploy(self, patch=False,domain=''):
        deploy_root = self.deploy_root + domain
        if not exists(self.deploy_root):
            run("mkdir -p %s" % self.deploy_root)
        with cd(self.deploy_root):
            u_domain = domain.replace('.','_')
            filename = "%s.wsgi"% u_domain
            context = {"user": env.user,
                       "project_name": env.project_name,
                       "u_domain":domain,
                       "root_domain":env.root_domain,
                       }
            wsgi_template = 'django-wsgi-template.txt'
            wsgi_exists = exists(filename)
            if wsgi_exists and not patch: 
                print env.host,"WSGI already exists on the host %s. Skipping..."% filename
                return False
            elif not wsgi_exists and patch:
                print env.host,"Error: Cannot patch %s wsgi. This version does not exist"% project_fullname
                return False
            current_version = active_version()
            if current_version == env.project_fullname and not patch:
                print env.host,"Warning: Cannot deploy wsgi, version %s already active. Increase the version and re-deploy. Skipping.."% env.project_fullname
                return False
            else: #not exists
                upload_template('woven/'+wsgi_template,
                                    filename,
                                    context,
                                )
                
                #finally set the ownership/permissions
                #We'll use the group to allow www-data execute 
                sudo("chown %s:www-data %s"% (env.user,filename))
                run("chmod ug+xr %s"% filename)
        set_server_state('deployed_wsgi_'+env.project_fullname)        
        

def deploy_wsgi(version='',patch=False):
    """
    wrapper around WSGI
    """
    if not env.DOMAINS: env.DOMAINS = [root_domain()]
    for domain in env.DOMAINS:
        w = WSGI(version)
        w.deploy(patch,domain)
        
    