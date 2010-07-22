#!/usr/bin/env python
from optparse import make_option

from fabric import state
from woven.api import setupnode
from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Setup a baseline Ubuntu server ready for deployment
    
    Basic Usage:
    ``python manage.py setupnode [user]@[hoststring]``
    
    Examples:
    ``python manage.py setupnode woven@192.168.188.10``
    ``python manage.py setupnode woven@host.example.com``
    
    """
    option_list = WovenCommand.option_list + (
        make_option('--overwrite', action='store_true', dest='overwrite', default=False,
            help='Overwrite any existing configuration files'),
    )
    help = "Setup a baseline Ubuntu host"
    requires_model_validation = False

    
    def handle_host(self,*args, **options):
        # Log to stdout
        setupnode(overwrite=options.get('overwrite'))


        
