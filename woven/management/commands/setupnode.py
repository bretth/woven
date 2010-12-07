#!/usr/bin/env python
from optparse import make_option

from django.utils import importlib

from fabric import state
from fabric.context_managers import settings
from fabric.main import is_task

from woven.api import setupnode, post_exec_hook
from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Setup a baseline linux server ready for deployment
    
    Basic Usage:
    ``python manage.py setupnode [user]@[hoststring]``
    
    Examples:
    ``python manage.py setupnode woven@192.168.188.10``
    ``python manage.py setupnode woven@host.example.com``
    
    """
    option_list = WovenCommand.option_list + (
        make_option('--root_disabled',
            action='store_true',
            default=False,
            help="Skip user creation and root disable"
        ),
        
    )
    help = "Setup a baseline linux host"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        state.env.root_disabled = options.get('root_disabled')
        setupnode()
        post_exec_hook('post_setupnode')
        



        
