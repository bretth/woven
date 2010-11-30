#!/usr/bin/env python
from optparse import make_option
import os

from fabric import state
from fabric.decorators import runs_once
from fabric.context_managers import settings
from fabric.operations import sudo
from fabric.contrib.files import exists

from woven.management.base import WovenCommand
from woven.webservers import _get_django_sites, deploy_wsgi, deploy_webconf, domain_sites, reload_webservers
from woven.project import deploy_sitesettings

class Command(WovenCommand):
    """
    Create sitesetting files for new django.contrib.sites.
    
    In django site creation is through the production database. The startsite command
    creates the sitesetting files for each of the new sites, and deploys them.
    
    Basic Usage:
    ``python manage.py startsite [hoststring|role]``
    
    """
    help = "Create a sitesetting file for new django sites"
    requires_model_validation = False

    def handle_host(self,*args, **options):
        with settings(patch=True):
            deploy_wsgi()
            deploy_webconf()
        
        activate_sites = [''.join([d.name.replace('.','_'),'-',state.env.project_version,'.conf']) for d in domain_sites()]
        site_paths = ['/etc/apache2','/etc/nginx']
        
        #activate new sites
        for path in site_paths:
            for site in activate_sites:
                if not exists('/'.join([path,'sites-enabled',site])):
                    sudo("chmod 644 %s" % '/'.join([path,'sites-available',site]))
                    sudo("ln -s %s/sites-available/%s %s/sites-enabled/%s"% (path,site,path,site))
                    if state.env.verbosity:
                        print " * enabled", "%s/sites-enabled/%s"% (path,site)
        reload_webservers()
        
     

