#!/usr/bin/env python
from optparse import make_option

from fabric.state import env

from woven.environment import project_version
from woven.virtualenv import activate
from woven.management.base import WovenCommand



class Command(WovenCommand):
    """
    Active a project version
    
    e.g. python manage.py activate 0.1
    """

    help = "Activate a version of your project"
    requires_model_validation = False
    args = "version user@ipaddress [host2...]"
    
    def parse_host_args(self, *args):
        """
        Returns a comma separated string of hosts
        """
        return ','.join(args[1:])
    
    def handle_host(self,*args, **options):
        vers = args[0]
        env.nomigration = True
        with project_version(vers):        
            activate()

        return