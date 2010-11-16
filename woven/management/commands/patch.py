#!/usr/bin/env python
from optparse import make_option

from fabric.context_managers import settings

from woven.api import deploy, activate
from woven.api import deploy_project, deploy_templates, deploy_static, deploy_media
from woven.api import deploy_wsgi, deploy_webconf

from woven.management.base import WovenCommand

class Command(WovenCommand):
    """
    Patch the current version of your project on hosts and restart webservices
    Includes project, web configuration, media, and wsgi but does not pip install
    
    Basic Usage:
    ``python manage.py patch [user]@[hoststring]``
    
    Examples:
    ``python manage.py patch woven@192.168.188.10``
    ``python manage.py patch woven@host.example.com``
    
    For just the current user
    ``python manage.py patch host.example.com``
    
    """

    help = "Patch all parts of the current version of your project, or patch part of the project"
    args = "[project|templates|static|media|wsgi|webconf] [user@hoststring ...]"
    requires_model_validation = False

    def parse_host_args(self, *args):
        """
        Splits out the patch subcommand and returns a comma separated list of host_strings
        """
        self.subcommand = None
        new_args = args
        try:
            sub = args[0]
            if sub in ['project','templates','static','media','wsgi','webconf']:
                self.subcommand = args[0]
                new_args = args[1:]
        except IndexError:
            pass
        
        return ','.join(new_args)
    
    def handle_host(self,*args, **options):
        with settings(patch=True):
            if not self.subcommand:
                deploy()
                activate()
            else:
                eval(''.join(['deploy_',self.subcommand,'()']))
                activate()


