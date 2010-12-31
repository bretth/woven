#!/usr/bin/env python
from optparse import make_option

from django.utils import importlib

from fabric import state

from woven.api import createnode, post_exec_hook
from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Create a node 
    
    Basic Usage:
    ``woven-admin.py createnode [user]@[hoststring]``
    
    Examples:
    ``woven-admin.py createnode woven@192.168.188.10``
    ``woven-admin.py createnode woven@host.example.com``
    
    """
    #option_list = WovenCommand.option_list + (
    #    make_option('--root_disabled',
    #        action='store_true',
    #        default=False,
    #        help="Skip user creation and root disable"
    #    ),
    #    
    #)
    help = "Create a node"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        createnode()
        post_exec_hook('post_createnode')