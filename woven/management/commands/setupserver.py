#!/usr/bin/env python
from optparse import make_option

from woven.main import setupserver
from woven.management.base import WovenCommand

class Command(WovenCommand):
    option_list = WovenCommand.option_list + (
        make_option('--overwrite', action='store_true', dest='overwrite', default=False,
            help='Overwrite any existing configuration files'),
    )
    help = "Setup Ubuntu Server Django stack "
    requires_model_validation = False
    
    def handle_host(self, **options):
        setupserver()


        
