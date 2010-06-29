#!/usr/bin/env python
from optparse import make_option

from fabric import state
from woven.main import setupnode
from woven.management.base import WovenCommand

class Command(WovenCommand):
    option_list = WovenCommand.option_list + (
        make_option('--overwrite', action='store_true', dest='overwrite', default=False,
            help='Overwrite any existing configuration files'),
    )
    help = "Setup a baseline Ubuntu host"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        # Log to stdout
        setupnode(overwrite=options.get('overwrite'))


        
