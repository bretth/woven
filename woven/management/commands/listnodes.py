#!/usr/bin/env python
from optparse import make_option
import sys

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from fabric import state

from libcloud.types import Provider

from woven.api import list_nodes, set_env

class Command(BaseCommand):
    """
    List node 
    
    Basic Usage:
    ``woven-admin.py listnodes [role or provider]``
    
    Examples:
    ``woven-admin.py listnodes web``
    ``woven-admin.py listnodes linode``
    
    """
    help = "List nodes"
    requires_model_validation = False
    
    def handle(self,*args, **options):
        """
        Initializes the node
        """
        self.style = no_style()
        #manage.py execution specific variables
        #verbosity 0 = No output at all, 1 = woven output only, 2 = Fabric outputlevel = everything except debug
        state.env.verbosity = int(options.get('verbosity', 1))

        #show_traceback = options.get('traceback', False)
        state.env.INTERACTIVE = options.get('interactive', True)

        set_env(settings)
        
        #Django passes in a dictionary instead of the optparse options objects
        for option in options:
            state.env[option] = options[option]

        confs = state.env.NODES
        named_conf = None
        drivers = [d.lower() for d in dir(Provider()) if d.isupper()]

        if not args:
            named_conf = 'default'
        else:
            named_conf = args[0]
        conf = confs.get(named_conf,{})
        if not conf:
            print "ERROR: You must define a NODES setting for '%s'"% named_conf
            sys.exit(1)
        provider = conf.get('PROVIDER')
        uid = conf.get('USER','')
        secret_key = conf.get('KEY','')        

        if not provider in drivers:
            print "default libcloud providers:"
            for d in drivers:
                print d
            print "Error: you must enter a single valid provider or define NODES in your settings"
            sys.exit(1)
            
        list_nodes(provider, secret_key, uid)
