#!/usr/bin/env python
from optparse import make_option

from fabric.context_managers import settings

from woven.api import deploy, activate
from woven.management.base import WovenCommand



class Command(WovenCommand):
    """
    Patch the current version of your project on hosts and restart webservices
    Includes project, web configuration, media, and wsgi but does not pip install
    
    Basic Usage:
    ``python manage.py patch [user]@[hoststring]``
    
    Examples:
    ``python manage.py patch woven@192.168.188.10``
    ``python manage.py patch woven@host.example.com``
    
    For just the current user
    ``python manage.py patch host.example.com``
    
    """
    option_list = WovenCommand.option_list + (

    )
    help = "Patch the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        with settings(patch=True):
            deploy()
            activate()


