#!/usr/bin/env python
"""
Test runner for woven.

Unit Tests don't appear to work with Fabric so all tests are run as fabfiles.
In absence of a better alternative the tests are split into separate files
with a specific naming strategy to make sure they run in groups.

``fab test`` will run all tests

To run individual tests:

``fab test_[test name]``

Tests are prefixed with an abbreviated name of the module they are testing so
that they run in groups, then alpha order.

Test functions defined in this file should be less than 10 characters in length.

"""
import os, string, sys

from django.utils import importlib
from fabric.state import commands, env
from woven.environment import set_env

#import tests
from env import test_env_server_state, test_env_parse_project_version, test_env_root_domain
from ubu import test_ubu_disable_root, test_ubu_change_ssh_port

#Set the environ for Django
settings_module = os.environ['DJANGO_SETTINGS_MODULE'] = 'example_project.settings'

#Normally you would run fab or manage.py under the setup.py path
#since we are testing outside the normal working directory we need to pass it in
setup_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],'simplest_example')
sys.path.insert(0,setup_dir)

env.verbosity = 2
#Most high level api functions require set_env to set the necessary woven environment
set_env(setup_dir=setup_dir)

def _run_tests(key=''):
    #Get a list of functions from fabric
    tests = commands.keys()
    for t in tests:
        if key:
            test_prefix = 'test_'+key+'_'
        else:
            test_prefix = 'test_'        
        if test_prefix in t and len(t)>10:
            print string.upper(t)
            commands[t]()    
            print string.upper(t), 'COMPLETE'
def test():
    """
    Run all tests (in alpha order)
    """
    _run_tests()
            
def test_env():
    """
    Run all environment tests
    """
    _run_tests('env')
    
def test_ubu():
    """
    Run all ubuntu tests
    """
    _run_tests('ubu')

