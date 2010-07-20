#!/usr/bin/env python
"""
Node command to execute arbitrary commands on a host.
"""
from optparse import make_option
from fabric.state import env
from fabric.context_managers import cd
from fabric.operations import run

from woven.management.base import WovenCommand
from woven.environment import set_project_env

class Command(WovenCommand):
    option_list = WovenCommand.option_list + (
        make_option('--options',
            help='Store all the management command options in a string. ie --options="--[opt]=[value] ..."'),
    )
    help = """Execute a management command on one or more hosts"""\
    """ Must not require user input"""
    requires_model_validation = False
    
    args = "command user@ipaddress ..."
    
    def parse_host_args(self, *args):
        """
        Splits out the management command and returns a comma separated list of host_strings
        """
        #This overrides the base command
        return ','.join(args[1:])
        
    def handle_host(self,*args, **options):
        set_project_env()
        opts = options.get('options')
        command = args[0]
        path = '/home/%s/%s/env/%s/project/%s/'% (env.user,root_domain(),env.project_fullname,env.project_name)
        print path
        pythonpath = '/home/%s/%s/env/%s/bin/python'% (env.user,env.root_domain,env.project_fullname)
        with cd(path):     
            result = run(' '.join([pythonpath,'manage.py',command,opts]))
        if env.verbosity:
            print result
        

