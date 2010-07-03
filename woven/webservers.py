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
from woven.utils import project_fullname, project_name, project_version, active_version
from woven.utils import upload_template

from woven.project import Project

def _ls_sites(path):
    """
    List only sites in the env.DOMAINS to ensure we co-exist with other projects
    
    """
    
    sites = run('ls %s'% path).split('\n')
    doms = env.DOMAINS
    dom_sites = []
    for s in sites:
        ds = s.split('-')[0]
        ds = ds.replace('_','.')
        if ds in doms and s not in dom_sites:
            dom_sites.append(s)
    return dom_sites

def sites_enabled():
    """
    Get a list of apache sites enabled
    """
    path = "/etc/apache2/sites-enabled/"
    if exists(path, use_sudo=True):
        sites_enabled = _ls_sites(path)
    return sites_enabled

class WSGI(Project):
    """
    Deploy a modwsgi file per domain and base class for webserver classes
    """
    
    state = 'deployed_wsgi_'
    def __init__(self,domain, version=''):
        super(WSGI,self).__init__(version)
        self.domain = domain
        self.template = 'django-wsgi-template.txt'
        
    
    def deploy(self, patch=False):
        
        if not exists(self.deploy_root):
            run("mkdir -p %s" % self.deploy_root)
        with cd(self.deploy_root):
            u_domain = self.domain.replace('.','_')
            filename = "%s.wsgi"% u_domain
            context = {"user": env.user,
                       "project_name": env.project_name,
                       "u_domain":u_domain,
                       "root_domain":env.root_domain,
                       }
            wsgi_exists = exists(filename)
            if wsgi_exists and not patch: 
                print env.host,"%s already exists on the host %s. Skipping..."% (self.deploy_type,filename)
                return False
            elif not wsgi_exists and patch:
                print env.host,"Error: Cannot patch %s %s. This version does not exist"% (project_fullname(), self.deploy_type)
                return False
            current_version = active_version()
            if current_version == env.project_fullname and not patch:
                print env.host,"Warning: Cannot deploy %s, version %s already active. Increase the version and re-deploy. Skipping.."% (self.deploy_type,env.project_fullname)
                return False
            else: #not exists
                upload_template('woven/'+self.template,
                                    filename,
                                    context,
                                )
                
                #finally set the ownership/permissions
                #We'll use the group to allow www-data execute
                if self.deploy_type == 'wsgi':
                    sudo("chown %s:www-data %s"% (env.user,filename))
                    run("chmod ug+xr %s"% filename)
        set_server_state(self.state+env.project_fullname)        
        

def deploy_wsgi(version='',patch=False):
    """
    wrapper around WSGI
    """
    if not env.DOMAINS: env.DOMAINS = [root_domain()]
    for domain in env.DOMAINS:
        w = WSGI(domain,version)
        w.deploy(patch)

class ApacheWebserver(Project):
    """
    Deploy Apache webserver configuration
    """
    state = 'deployed_apache_webserver_'
    def __init__(self,domain,version=''):
        super(ApacheWebserver,self).__init__(version)
        self.domain = domain
        self.template = 'django-apache-template.txt'
        self.deploy_root = "/etc/apache2/sites-available/"
        self.enabled_path = "/etc/apache2/sites-enabled/"
        self.version = project_version(version)
        if not 'http:' in env.MEDIA_URL: self.media_url = env.MEDIA_URL
        else: self.media_url = ''
        if not 'http:' in env.STATIC_URL: self.static_url = env.STATIC_URL
        else: self.static_url = ''            

    
    def deploy(self,patch=False):
        with cd(self.deploy_root):

            log_dir = env.deployment_root+'log'
            if not exists(log_dir):
                run("mkdir -p %s"% log_dir)
                sudo("chown -R www-data:sudo %s" % log_dir)
                sudo("chmod -R ug+w %s"% log_dir)
            u_domain = self.domain.replace('.','_')

            filename = u_domain + '-'+self.version+'.conf'
            context = {"project_name": env.project_name,
                        "u_domain":u_domain,
                        "domain":self.domain,
                        "root_domain":env.root_domain,
                        "user":env.user,
                        "host_ip":env.host,
                        "media_url":self.media_url,
                        "static_url":self.static_url,
                        }
                
            conf_exists = exists(os.path.join(self.enabled_path,filename), use_sudo=True)
            state = server_state(self.state+env.project_fullname)

            if not conf_exists and patch:
                if env.verbosity:
                    print env.host,"Cannot patch %s conf %s. This version does not exist on %s. Skipping"% (self.deploy_type, filename, env.host)
                return False
            elif state and not patch: #active version
                print "%s conf %s already exists on the host %s. Skipping"% (self.deploy_type, filename, env.host)
                return False
            else:
                enabled_sites = _ls_sites(self.enabled_path)
                if not patch:
                    for site in enabled_sites:
                        if env.verbosity:
                            print env.host,'Disabling', site, filename
                        sudo("rm %s%s"% (self.enabled_path,site))

                upload_template('woven/'+self.template,
                                filename,
                                context,
                                use_sudo=True)
                if not patch:
                    #enable this site
                    sudo("chmod 644 %s" % filename)
                    if not exists(self.enabled_path+ filename):
                        sudo("ln -s %s%s %s%s"% (self.deploy_root,filename,self.enabled_path,filename))
        set_server_state(self.state + self.fullname)
        if env.verbosity:
            print env.host,'DEPLOYED',self.deploy_type
        
    def delete(self):
        pass

class NginxWebserver(ApacheWebserver):
    state = 'deployed_nginx_webserver_'
    def __init__(self,domain, version=''):
        super(NginxWebserver,self).__init__(domain,version)
        self.template = 'nginx-template.txt'
        self.deploy_root = "/etc/nginx/sites-available/"
        self.enabled_path = "/etc/nginx/sites-enabled/"
        
def deploy_webservers(version='',patch=False):
    """ Deploy  apache & nginx site configurations to the host """
    if not env.DOMAINS: env.DOMAINS = [root_domain()]
    #TODO - incorrect - check for actual package
    if exists('/etc/apache2/sites-enabled/') and exists('/etc/nginx/sites-enabled'):

        for d in env.DOMAINS:
            a = ApacheWebserver(d,version)
            a.deploy(patch)
            
            n = NginxWebserver(d,version)
            n.deploy(patch)
        set_server_state('deployed_webservers_' + project_fullname())
        return True

    else:
        print env.host,"""WARNING: Apache or Nginx not installed"""
        return False
    return False

def stop_webservices():
    #TODO - distinguish between a warning and a error on apache
    if env.verbosity:
        print env.host,"STOPPING nginx"
    sudo("/etc/init.d/nginx stop")

    with settings(warn_only=True):
        if env.verbosity:
            print env.host,"STOPPING apache2"
        a = sudo("apache2ctl stop")
        
    return True

def start_webservices():
    with settings(warn_only=True):
        if env.verbosity:
            print env.host,"STARTING apache2"
        a = sudo("apache2ctl start")
    if a.failed and env.verbosity:
        print env.host, a
        return False
    if env.verbosity:
        print env.host,"STARTING nginx"
    sudo("/etc/init.d/nginx start")
    return True

    