#!/usr/bin/env python
from optparse import make_option
from glob import glob
import os

from django.core.management.base import BaseCommand
from django.core.management.color import no_style

from fabric import state
from fabric.operations import local
from fabric.context_managers import hide

from woven.environment import set_env

class Command(BaseCommand):
    """
    Pip bundle your requirements into .pybundles for efficient deployment
    
    python manage.py bundle
    """    
    help = "Pip bundle your requirements into .pybundles for efficient deployment"
    args = ""
    requires_model_validation = False
    
    def handle(self, *args, **options):
        
        self.style = no_style()
        #manage.py execution specific variables
        #verbosity 0 = No output at all, 1 = woven output only, 2 = Fabric outputlevel = everything except debug
        state.env.verbosity = int(options.get('verbosity', 1))

        #show_traceback = options.get('traceback', False)
        set_env.no_domain = True
        state.env.INTERACTIVE = options.get('interactive')
        if int(state.env.verbosity) < 2:
            with hide('warnings', 'running', 'stdout', 'stderr'):
                set_env()
        else:
            set_env()
        if not state.env.PIP_REQUIREMENTS: req_files = glob('req*')
        else: req_files = state.env.PIP_REQUIREMENTS
        dist_dir = os.path.join(os.getcwd(),'dist')
        if not os.path.exists(dist_dir):
            os.mkdir(dist_dir)
        for r in req_files:
            bundle = ''.join([r.split('.')[0],'.pybundle'])
            command = 'pip bundle -r %s %s/%s'% (r,dist_dir,bundle)
            if state.env.verbosity: print command
            if int(state.env.verbosity) < 2:
                with hide('warnings', 'running', 'stdout', 'stderr'):
                    local(command)
            else:
                local(command)
        
        