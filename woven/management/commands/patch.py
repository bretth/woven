#!/usr/bin/env python
from optparse import make_option


from woven.api import deploy, activate
from woven.management.base import WovenCommand
from woven.environment import set_project_env


class Command(WovenCommand):
    option_list = WovenCommand.option_list + (

    )
    help = "Patch the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        set_project_env()
        with settings(patch=True):
            deploy()
            activate


