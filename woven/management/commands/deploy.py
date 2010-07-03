#!/usr/bin/env python
from optparse import make_option

from woven.main import deploy
from woven.management.base import WovenCommand

class Command(WovenCommand):

    help = "Deploy the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        # Log to stdout
        deploy()

