#!/usr/bin/env python
from optparse import make_option

from woven.api import deploy
from woven.virtualenv import activate
from woven.management.base import WovenCommand


class Command(WovenCommand):
    """
    Deploy your project to a host and activate
    
    Basic Usage:
    ``python manage.py deploy [user]@[hoststring]``
    
    Examples:
    ``python manage.py deploy woven@192.168.188.10``
    ``python manage.py deploy woven@host.example.com``
    
    For just the current user
    ``python manage.py deploy host.example.com``
    
    """

    help = "Deploy the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        deploy()
        activate()

