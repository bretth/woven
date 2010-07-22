#!/usr/bin/env python
import socket

from fabric.state import env
from fabric.operations import run, sudo
from fabric.context_managers import cd, settings
from fabric.contrib.files import exists
#Required for a bug in 0.9
from fabric.version import get_version

from woven.deployment import deploy_files, mkdirs, run_once_per_host_version, upload_template
from woven.environment import deployment_root

def _activate_sites(path, filenames):
    enabled_sites = _ls_sites(path)            
    for site in enabled_sites:
        if env.verbosity:
            print env.host,'Disabling', site
        if site not in filenames:
            sudo("rm %s/%s"% (path,site))
        
        sudo("chmod 644 %s" % site)
        if not exists('/etc/apache2/sites-enabled'+ filename):
            sudo("ln -s %s%s %s%s"% (self.deploy_root,filename,self.enabled_path,filename))

def _deploy_webserver(remote_dir,template):
    
    if not 'http:' in env.MEDIA_URL: media_url = env.MEDIA_URL
    else: media_url = ''
    if not 'http:' in env.STATIC_URL: static_url = env.STATIC_URL
    else: static_url = ''    
    log_dir = '/'.join([deployment_root(),'log'])
    deployed = []

    for d in env.DOMAINS:

        u_domain = d.replace('.','_')

        filename = ''.join([remote_dir,'/',u_domain,'-',env.project_version,'.conf'])
        context = {"project_name": env.project_name,
                    "u_domain":u_domain,
                    "domain":d,
                    "root_domain":env.root_domain,
                    "user":env.user,
                    "host_ip":socket.gethostbyname(env.host),
                    "media_url":media_url,
                    "static_url":static_url,
                    }

        upload_template('/'.join(['woven',template]),
                        filename,
                        context,
                        use_sudo=True)
        if env.verbosity:
            print " * uploaded", filename

    return deployed

def _ls_sites(path):
    """
    List only sites in the env.DOMAINS to ensure we co-exist with other projects
    """
    with cd(path):
        sites = run('ls').split('\n')
        doms = env.DOMAINS
        dom_sites = []
        for s in sites:
            ds = s.split('-')[0]
            ds = ds.replace('_','.')
            if ds in doms and s not in dom_sites:
                dom_sites.append(s)
    return dom_sites

@run_once_per_host_version
def deploy_webservers():
    """ Deploy apache & nginx site configurations to the host """
    deployed = []
    log_dir = '/'.join([deployment_root(),'log'])
    #TODO - incorrect - check for actual package to confirm installation
    if exists('/etc/apache2/sites-enabled/') and exists('/etc/nginx/sites-enabled'):
        if env.verbosity:
            print env.host,"DEPLOYING webserver configuration:"
        if not exists(log_dir):
            deployed += mkdirs(log_dir)
            sudo("chown -R www-data:sudo %s" % log_dir)
            sudo("chmod -R ug+w %s"% log_dir)
        deployed += _deploy_webserver('/etc/apache2/sites-available','django-apache-template.txt')
        deployed += _deploy_webserver('/etc/nginx/sites-available','nginx-template.txt')
    else:
        print env.host,"""WARNING: Apache or Nginx not installed"""
        
    return deployed

@run_once_per_host_version
def deploy_wsgi():
    """
    deploy python wsgi file(s)
    """
    remote_dir = '/'.join([deployment_root(),'env',env.project_fullname,'wsgi'])
    deployed = []
    if env.verbosity:
        print env.host,"DEPLOYING wsgi", remote_dir
    for domain in env.DOMAINS:
        deployed += mkdirs(remote_dir)
        with cd(remote_dir):
            u_domain = domain.replace('.','_')
            filename = "%s.wsgi"% u_domain
            context = {"user": env.user,
                       "project_name": env.project_name,
                       "u_domain":u_domain,
                       "root_domain":env.root_domain,
                       }
            upload_template('/'.join(['woven','django-wsgi-template.txt']),
                                filename,
                                context,
                            )
            if env.verbosity:
                print " * uploaded", filename
            #finally set the ownership/permissions
            #We'll use the group to allow www-data execute
            sudo("chown %s:www-data %s"% (env.user,filename))
            run("chmod ug+xr %s"% filename)
    return deployed

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

    