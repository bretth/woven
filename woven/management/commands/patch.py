#!/usr/bin/env python
from optparse import make_option


from woven.main import patch
from woven.management.base import WovenCommand

class Command(WovenCommand):
    option_list = WovenCommand.option_list + (

    )
    help = "Patch the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        # Log to stdout
        patch()

