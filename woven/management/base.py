#!/usr/bin/env python

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from fabric import state 
from fabric.main import _merge
from fabric.network import normalize
from fabric.context_managers import hide,show

from woven.environment import set_env

class WovenCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--noinput', action='store_false', dest='interactive', default=True,
            help='Do NOT prompt for input (except password entry if required)'),
        make_option('-r', '--reject-unknown-hosts',
            action='store_true',
            default=False,
            help="reject unknown hosts"
        ),
    
        make_option('-D', '--disable-known-hosts',
            action='store_true',
            default=False,
            help="do not load user known_hosts file"
        ),
        make_option('-u', '--user',
            default=state._get_system_username(),
            help="username to use when connecting to remote hosts"
        ),
    
        make_option('-p', '--password',
            default=None,
            help="password for use with authentication and/or sudo"
        ),
    
        make_option('-H', '--hosts',
            default=[],
            help="comma-separated list of hosts to operate on"
        ),
        #TODO
        #make_option('-R', '--roles',
        #    default=[],
        #    help="comma-separated list of roles to operate on"
        #),
        make_option('--setup',
            help='The /path/to/dir containing the setup.py module. The command will execute from this directory. Only required if you are not executing the command from below the setup.py directory',
        ),
        
    )
    help = ""
    args = "host1 [host2 ...] or user@host1 ..."
    requires_model_validation = False

  
    def handle_host(self, *args, **options):
        """
        This will be executed per host - override in subclass
        """
    def parse_host_args(self, *args):
        """
        Returns a comma separated string of hosts
        """
        return ','.join(args)
        
    def handle(self, *args, **options):
        """
        Initializes the fabric environment
        """
        self.style = no_style()
        #manage.py execution specific variables
        #verbosity 0 = No output at all, 1 = woven output only, 2 = Fabric outputlevel = everything except debug
        state.env.verbosity = int(options.get('verbosity', 1))

        #show_traceback = options.get('traceback', False)
        state.env.INTERACTIVE = options.get('interactive')
        
        #Fabric options
        #Django passes in a dictionary instead of the optparse options objects
        for option in options:
            state.env[option] = options[option]

        #Hosts can be args or options
        #args will be tuple, --host option will be same as Fabric
        if args: state.env.hosts = self.parse_host_args(*args)

        #This next section is taken pretty much verbatim from fabric.main
        #so we follow an almost identical but more limited execution strategy
        
        # Handle --hosts, --roles (comma separated string => list)
        for key in ['hosts', 'roles']:
            if key in state.env and isinstance(state.env[key], str):
                state.env[key] = state.env[key].split(',')
        
        #We now need to load django project woven settings into env
        #This is the equivalent to module level execution of the fabfile.py.
        #If we were using a fabfile.py then we would include set_env()

        if int(state.env.verbosity) < 2:
            with hide('warnings', 'running', 'stdout', 'stderr'):
                set_env(settings,state.env.setup)
        else: set_env(settings,state.env.setup)
        
        #Back to the standard execution strategy
        # Set current command name (used for some error messages)
        #state.env.command = self.name
        # Set host list (also copy to env)
        state.env.all_hosts = hosts = _merge(state.env.hosts,state.env.roles)
        # If hosts found, execute the function on each host in turn
        for host in hosts:
            # Preserve user
            prev_user = state.env.user
            # Split host string and apply to env dict
            #TODO - This section is replaced by network.interpret_host_string in Fabric 1.0
            username, hostname, port = normalize(host)
            state.env.host_string = host
            state.env.host = hostname
            state.env.user = username
            state.env.port = port

            # Actually run command
            if int(state.env.verbosity) < 2:
                with hide('warnings', 'running', 'stdout', 'stderr'):
                    self.handle_host(*args, **options)
            else:
                self.handle_host(*args, **options)
            # Put old user back
            state.env.user = prev_user
