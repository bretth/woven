#!/usr/bin/env python
"""
Tests file for woven. Unit Testing doesn't appear to work with Fabric
so we'll hold all our tests as a fabfile.
Requires the settings file for example_project.settings
to be setup in the environment variable DJANGO_SETTINGS_MODULE

"""
import os
import sys
import time

from fabric.api import env, run, local, sudo
from fabric.state import output
from fabric.contrib.files import exists
from fabric.context_managers import settings

from woven.ubuntu import disable_root, upload_ssh_key, change_ssh_port, restrict_ssh
from woven.ubuntu import uncomment_sources, upgrade_ubuntu, setup_ufw, install_packages, set_timezone
from woven.utils import server_state, set_server_state, root_domain
from woven.virtualenv import mkvirtualenv, rmvirtualenv
from woven.management.base import WovenCommand
from woven.main import setup_environ, setupnode
from woven.pip import pip_install_requirements


#Test the setup_environ indirectly by calling the management command 
settings_module = os.environ['DJANGO_SETTINGS_MODULE']
assert settings_module== 'example_project.settings'
setup_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],'simplest_example')
sys.path.insert(0,setup_dir)

#Simulate command line
c = WovenCommand()
c.handle(hosts='woven@192.168.188.10',interactive=False,setup=setup_dir, verbosity=2)

assert env.INTERACTIVE==False
assert env.host == '192.168.188.10'
#assert env.port == 10022
#User falls back to the system user after command execution
assert env.user == os.environ['USER']
env.user = 'woven'

#woven injects the custom ssh port into host string
assert env.host_string == 'woven@192.168.188.10:10022'

env.INTERACTIVE = False
env.HOST_PASSWORD = env.password = 'woven'
env.ROOT_PASSWORD = 'root'

def test_setup_environ():
    pass

def test_server_state():
    set_server_state('example',delete=True)
    set_server_state('example')
    print 'Server State:%s:'% str(server_state('example'))
    assert server_state('example') == True
    set_server_state('example',content='something')
    assert server_state('example') == 'something'
    assert server_state('example')
    
    
#Tests are in execution order of a normal setup, deploy, patch scenario

#Step 1 in the server setup process


def test_change_ssh_port():
    change_ssh_port()
    print "test logging in on the new port"
    
    with settings(host_string='root@192.168.188.10:10022',user='root',password=env.ROOT_PASSWORD):
        try:
            run('echo')
        except:
            print "\nTEST: change_ssh_port FAILED"
            return
        print 'CHANGE PASSED'
    print "ROLLBACK"
    assert change_ssh_port(rollback=True)
    print "TESTING ROLLBACK AGAIN"
    assert change_ssh_port(rollback=True)==False
    print "\nTEST: change_ssh_port PASSED"
    return

#Step 2 in Server setup process

def test_disable_root():
    #These two functions would normally be run as a pair
    #until we can find a way of testing that the function has already been run
    #since disabling root can only be run once
    print 'TEST DISABLE ROOT',env.host_string,env.port,env.user,env.host
    port_changed = change_ssh_port()
    assert port_changed
    if port_changed:
        disable_root()
    assert exists('/home/woven')

    
#Step 3 - Part 1
def test_upload_ssh_key():
    """
    Tests uploading an ssh key and using contextual settings
    """
    upload_ssh_key()
    assert exists('/home/woven/.ssh/authorized_keys')

#Step 3 - Part 2
def test_restrict_ssh():
    """
    Test ssh functions together
    """
    #setup
    port_changed = change_ssh_port()
    if port_changed:
        disable_root()
    upload_ssh_key()
    
    #test
    restrict_ssh()
    assert exists('/home/woven/.ssh/authorized_keys')

#Step 4 - part 1
def test_uncomment_sources():
    uncomment_sources()
    
#Step 4 - part 2
def test_upgrade_ubuntu():
    upgrade_ubuntu()

#Step 5 in setup
def test_setup_ufw():
    #setup
    port_changed = change_ssh_port()
    if port_changed:
        disable_root()
    upload_ssh_key()
    restrict_ssh()
    uncomment_sources()
    
    #test
    setup_ufw()

#Step 6 in setup
def test_install_packages():
    install_packages()
    
def test_install_packages_rollback():
    install_packages()
    
#Step 7 in setup
def test_set_timezone():
    set_timezone()
    
#Test the whole setup    
def test_setupnode():
    #limit the packages for this
    env.BASE_PACKAGES= ['python-setuptools','apache2','libapache2-mod-wsgi','nginx']
    setupnode()

def test_setupnode_rollback():
    print "TESTING ROLLBACK SETUPSERVER"
    #output['debug']=True
    setupnode(rollback=True)

### DEPLOYMENT TESTS

# Test related util functions
def test_root_domain():
    #In the event of noinput, the domain will default to example.com
    domain = root_domain()
    assert domain == 'example.com'

# First Deployment step
def test_virtualenv():
    #Ensure we're cleared out
    set_server_state('created_virtualenv_example_project-0.1', delete=True)
    set_server_state('created_virtualenv_example_project-0.2', delete=True)
    v = mkvirtualenv()
    #Returns True if it is created
    assert v
    assert exists('/home/woven/example.com/env/example_project-0.1/bin/python')
    
    v = mkvirtualenv()
    #Returns False if not created.
    assert not v
    
    #test updating the version no#
    v = mkvirtualenv('0.2')
    
    #teardown
    assert exists('/home/woven/example.com/env/example_project-0.2/bin/python')
    rmvirtualenv('0.2')
    assert not exists('/home/woven/example.com/env/example_project-0.2/bin/python')
    assert exists('/home/woven/example.com/env/example_project-0.1/bin/python')
    rmvirtualenv()
    assert not exists('/home/woven/example.com')
    assert not server_state('created_virtualenv_example_project-0.2')

def bundle():
    local('pip bundle -r requirements.txt dist/example_project.pybundle')

#Second deployment step
def test_pip_install_requirements():
    #Ensure nothing already there
    local('rm -f dist/example_project.pybundle')
    rmvirtualenv()
    set_server_state('pip_installed_example_project-0.1', delete=True)
    
    #Try installing without an virtual env which should fail
    p = pip_install_requirements()
    assert not p
    v = mkvirtualenv()

    #Install our example staticfiles
    p = pip_install_requirements()
    assert p
    assert exists('/home/woven/example.com/env/example_project-0.1/lib/python2.6/site-packages/staticfiles')
    
    #Try installing again - should fail
    p = pip_install_requirements()
    assert not p
    
    #Try rolling back installation
    pip_install_requirements(rollback=True)
    assert not exists('/home/woven/example.com/env/example_project-0.1/lib/python2.6/site-packages/staticfiles')
    
    #Bundle something up into the dist directory
    bundle()
    p = pip_install_requirements()
    assert exists('/home/woven/example.com/dist/example_project.pybundle')
    assert exists('/home/woven/example.com/env/example_project-0.1/lib/python2.6/site-packages/staticfiles')
    
    #Finally clean up 
    pip_install_requirements(rollback=True)  
    rmvirtualenv()
    local('rm -f dist/example_project.pybundle')
   
def test_project_version():
    """
    Test the project version
    """
    v = project_version('0.1')
    env.project_version = ''
    assert v == '0.1'
    v = project_version('0.1.0.1')
    env.project_version = ''
    assert v == '0.1'
    v = project_version('0.1 alpha')
    env.project_version = ''
    assert v =='0.1-alpha'
    v = project_version('0.1a 1234')
    env.project_version = ''
    assert v == '0.1a'
    v = project_version('0.1-alpha')
    env.project_version = ''
    assert v == '0.1-alpha'
    v = project_version('0.1 rc1 1234')
    env.project_version = ''
    assert v == '0.1-rc1'
    v = project_version('0.1.0rc1')
    env.project_version = ''
    assert v == '0.1.0rc1'
    v = project_version('0.1.1 rc2')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = project_version('0.1.1.rc2.1234')
    env.project_version = ''
    assert v == '0.1.1.rc2'
    v = project_version('0.1.1-rc2.1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = project_version('0.1.1-rc2-1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = project_version('0.1.1 rc2 1234')
    assert v ==  '0.1.1-rc2'  
    