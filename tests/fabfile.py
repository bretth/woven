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

from django.template.loader import render_to_string

from fabric.operations import _AttributeString
from fabric.api import *
from fabric.contrib.files import uncomment, exists

from woven.management.base import WovenCommand
from woven.api import *
from woven.environment import _parse_project_version, disable_virtualenvwrapper, enable_virtualenvwrapper
from woven.project import _make_local_sitesettings


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

#setup for the deployment functions


#Test utils

def test_project_name():
    print project_name()

def test_project_version():
    with project_version('0.2'):
        print 'env.project_fullname',env.project_fullname
        print 'env.project_name',env.project_name
        print 'env.project_full_version',env.project_full_version
        print 'evn.project_version',env.project_version
 
def test_project_fullname():
    print project_fullname()
    print env.project_fullname
    print env.project_name
    print env.project_version
    

def test_setenv():
    print "Determine that we are getting sitesettings"
    local('rm -rf example_project/sitesettings')
    #Prior to creating the sitesettings it should be whatever the default dev setting is
    print env.MEDIA_ROOT <> '/home/woven/public/'
    deployment_root()
    _make_local_sitesettings()
    set_env()


def test_server_state():
    set_server_state('example',delete=True)
    set_server_state('example')
    print 'Server State:%s:'% str(server_state('example'))
    print server_state('example')
    assert server_state('example')
    set_server_state('example',object=['something'])
    state = server_state('example')
    assert state.object == ['something']
    set_server_state('example',delete=True)
    state = server_state('example')
    assert not state
    print state
   
def test_stage_local_files():
    #setup
    local_dir = os.path.join(os.getcwd(),'templates')
    local_files = {}
    context={'title':'some_title','body':'somebody'}
    
    #test coverting all files as templates - contect supplied
    print "TEST 1"
    staging_dir = _stage_local_files(local_dir,{},context)
    print staging_dir
    rs = local('cat '+staging_dir+'/app/template')
    assert  'somebody' in rs
    assert os.path.exists(os.path.join(staging_dir,'index.html'))
    
    #test staging specific template files with context
    print "TEST 2"
  
    local_files = _get_local_files(local_dir, pattern='app/*')
    staging_dir = _stage_local_files(local_dir,local_files,context)
    rs = local('cat '+staging_dir+'/app/template')
    assert  'somebody' in rs
    assert not os.path.exists(os.path.join(staging_dir,'index.html'))
    
    print "TEST 3"
    #test staging specific files without context
    context = {}
    local_files = _get_local_files(local_dir, pattern='app/*')
    staging_dir = _stage_local_files(local_dir,local_files,context)
    rs = local('cat '+staging_dir+'/app/template')
    assert not 'somebody' in rs
    assert not os.path.exists(os.path.join(staging_dir,'index.html'))
 
def test_deploy_files():
    run('rm -rf /home/woven/test')
    local_dir = os.path.join(os.getcwd(),'templates')
    context={'title':'some_title','body':'somebody'}
    
    remote_dir = '/home/woven/test'
    files = deploy_files(local_dir, remote_dir, pattern = 'app/*', context=context)
    print "TEST_DEPLOYED_FILES"
    assert exists('/home/woven/test/app/template')
    
    run('rm -rf /home/woven/test')
    #test deploying a simple directory
    files = deploy_files(local_dir,remote_dir)
    assert exists('/home/woven/test/app/template')
    assert exists('/home/woven/test/index.html')
    
    print "TEST RE-DEPLOY FILES"
    
    files = deploy_files(local_dir,remote_dir)
    assert not files
    run('rm -rf /home/woven/test')

def test_get_sites():
    print env.all_hosts
    _get_sites()

def test_run_once_per_version():
    sudo('rm -rf /var/local/woven')
    @run_once_per_version
    def test():
        a = State('SomeString')
        a.failed=False
        return a
    
    result = test()
    assert result
    assert result == 'SomeString'
    print result
    assert exists('/var/local/woven/test-example_project-0.1')
    result = test()
     
    assert not result.failed
    env.patch=True
    result = test()
    assert result == 'SomeString'
    sudo('rm -rf /var/local/woven')
    result = test()
    assert result.failed
   
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
    
#Step 8 in setup
def test_deploy_db():
    #Test initial database deployment
    deploy_db()
    
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

def deploy_teardown():
    with hide('running', 'stdout'):
        local('rm -f dist/requirements1.pybundle')
        local('rm -f requirements.txt')
        local('rm -f requirements1.txt')
        local('rm -f pip*')
        local('rm -rf example_project/sitesettings')
        with settings(warn_only=True):
            local('cp -f example_project/original_settings.py example_project/settings.py')
        sudo('rm -rf /var/local/woven')
        sudo('rm -rf /home/woven/env')
        sudo('rm -rf /home/woven/public')
        sudo('rm -rf /home/woven/static')
        sudo('rm -rf /home/woven/log')
        sudo('rm -rf /home/woven/database')
        sudo('rm -f /etc/nginx/sites-enabled/*')
        sudo('rm -f /etc/nginx/sites-available/*')
        sudo('rm -f /etc/apache2/sites-enabled/*')
        sudo('rm -f /etc/apache2/sites-available/*')
        sudo('rm -rf /home/woven/workon-example_project')
        sudo('rm -f /etc/nginx/sites-enabled/someother_com-0.1.conf')
        sudo('rm -rf /home/woven/*')
    


# Test related util functions
def test_root_domain():
    #In the event of noinput, the domain will default to example.com
    domain = _root_domain()
    print domain
    assert domain == 'example.com'

# First Deployment step
def test_mkvirtualenv():
    
    #Ensure we're cleared out settings
    sudo('rm -rf /var/local/woven')
    sudo('rm -rf /home/woven/env')
    v = mkvirtualenv()
    #Returns True if it is created
    print v.object
    print v.failed
    assert v
    assert exists('/home/woven/env/example_project-0.1/bin/python')
    
    v = mkvirtualenv()
    #Returns True if already created.
    assert v
    
    #test updating the version no#
    with project_version('0.2'):
        print 'Installing version 0.2'
        print env.project_version
        #print project_fullname()
        v = mkvirtualenv()
    
    #teardown
    #assert exists('/home/woven/env/example_project-0.2/bin/python')
    #with project_version('0.2'):
    #    rmvirtualenv()
    #    assert not exists('/home/woven/env/example_project-0.2/bin/python')
    #    assert not server_state('mkvirtualenv')
    #assert exists('/home/woven/env/example_project-0.1/bin/python')
    #rmvirtualenv()
    #assert not exists('/home/woven/env')
    #assert not server_state('mkvirtualenv')

def bundle():
    local('pip bundle -r requirements1.txt dist/requirements1.pybundle')

#Second deployment step
def test_pip_install_requirements():
    #output.debug = True
    #Ensure nothing already there
    deploy_teardown()

    rmvirtualenv()
    #Try installing without an virtual env which should fail
    p = pip_install_requirements()
    assert not p
    v = mkvirtualenv()
    #c = confirm('PROCEED Install Just woven & django')
    print "INSTALL Just woven & django"
    env.DJANGO_REQUIREMENT='file://'+os.path.join(os.getcwd(),'dist','Django-1.2.1.tar.gz')
    p = pip_install_requirements()
    assert exists('/home/woven/env/example_project-0.1/lib/python2.6/site-packages/django')
    ##Install our example staticfiles
    #c = confirm('PROCEED Install staticfiles')
    print " INSTALL staticfiles"
    set_server_state('pip_install_requirements', delete=True)
    local("echo 'django-staticfiles' >> requirements1.txt")
    p = pip_install_requirements()
    assert p
    assert exists('/home/woven/env/example_project-0.1/lib/python2.6/site-packages/staticfiles')
    #c = confirm('PROCEED fail test')
    #Try installing again - should show installed
    p = pip_install_requirements()
    assert p

    #c = confirm('PROCEED bundle')
    print "Bundle something up into the dist directory"
    set_server_state('pip_install_requirements', delete=True)
    bundle()
    p = pip_install_requirements()
    assert exists('/home/woven/env/example_project-0.1/dist/requirements1.pybundle')
    assert exists('/home/woven/env/example_project-0.1/lib/python2.6/site-packages/staticfiles')

def test_pip_install_fail():
    print "TEST_PIP_INSTALL_FAIL"
    deploy_teardown()
    
    v = mkvirtualenv()
    env.DJANGO_REQUIREMENT='Drongo'
    p = pip_install_requirements()
    print 'FAILED:',p.failed
    print 'STDERR:',p.stderr

def test_deploy_project():
    #setup to ensure nothing left from a previous run
    deploy_teardown()
    
    #tests
    deploy_project()
    assert exists('/home/woven/env/example_project-0.1/project/setup.py')
    assert exists('/home/woven/env/example_project-0.1/project/example_project/sitesettings/example_com.py')
    assert contains('from example_project.settings import','/home/woven/example.com/env/example_project-0.1/project/example_project/sitesettings/example_com.py')
    
    #Test deploy version '0.2'
    with project_version('0.2'):
        deploy_project()
        assert exists('/home/woven/env/example_project-0.2/project/setup.py')

    
def test_deploy_static():
    deploy_teardown()
    
    #Test simple with no app media
    with settings(INSTALLED_APPS=[]):
        deploy_static()
    
    #Test with just admin_media
    env.INSTALLED_APPS += ['django.contrib.admin']
    deploy_static()
    assert exists('/home/woven/env/example_project-0.1/static/static/admin-media/css')
 

def test_deploy_public():
    deploy_teardown()

    with settings(MEDIA_ROOT=''):
    #Test simple with no media_root - fails
        deploy_public()
    
    #Test with a real media directory
    
    print 'MEDIA_ROOT', env.MEDIA_ROOT

    deploy_public()
    assert exists('/home/woven/public/media/django-pony.jpg')

def test_deploy_templates():
    #teardown
    deploy_teardown()
    
    #simple deploy with no templates defined
    with settings(TEMPLATE_DIRS=()):
        deploy_templates()
   

    deploy_templates()
    assert exists('/home/woven/env/example_project-0.1/templates/index.html')
    
def test_deploy_wsgi():
    deploy_teardown()

    deploy_wsgi()
    assert exists('/home/woven/env/example_project-0.1/wsgi/example_com.wsgi')
    
def test_deploy_webservers():
    #setup for test
    deploy_teardown()
    #Initial test
    print "SIMPLE TEST"
    deploy_webservers()
    assert exists('/etc/apache2/sites-available/example_com-0.1.conf')
    assert exists('/etc/nginx/sites-available/example_com-0.1.conf',)


    print "BUMP VERSION TO 0.2"
    
    with project_version('0.2'):
        deploy_webservers()
    assert exists('/etc/apache2/sites-available/example_com-0.2.conf')

def test_webservices():
    #Test start and stop webservices
    sudo('rm -rf /home/woven/example.com')
    sudo('rm -f /etc/nginx/sites-enabled/*')
    sudo('rm -f /etc/nginx/sites-available/*')
    sudo('rm -f /etc/apache2/sites-enabled/*')
    sudo('rm -f /etc/apache2/sites-available/*')
    set_server_state('deployed_apache_webserver_example_project-0.1',delete=True)
    set_server_state('deployed_nginx_webserver_example_project-0.1',delete=True)
    stop_webservices()
    
    deploy_webservers()
    start_webservices()
    stop_webservices()
    stop_webservices()
    start_webservices()
    start_webservices()
    #stop_webservices()

def test_activate():
    deploy_teardown()
    
    mkvirtualenv()
    #deploy_db()
    deploy_project()
    deploy_wsgi()
    deploy_public()
    deploy_static()
    deploy_webservers()
   
    activate()
    
    #try with version 0.2
    with project_version('0.2'):
        deploy_project()
        deploy_wsgi()
        deploy_public()
        deploy_static()
        deploy_webservers()
        sudo('cp /etc/nginx/sites-available/example_com-0.1.conf /etc/nginx/sites-enabled/someother_com-0.1.conf')
        sed(filename='/etc/nginx/sites-enabled/someother_com-0.1.conf',before='example.com',after='someexample.com', limit=2,use_sudo=True)
        sudo('rm -f /etc/nginx/sites-enabled/someother_com-0.1.conf.bak')
        activate()
        assert exists('/etc/nginx/sites-enabled/someother_com-0.1.conf')

def test_migration():
    deploy_teardown()
    
    #setup
    f = open("requirements.txt","w+")
    text = render_to_string('woven/requirements.txt')
    f.write(text)
    f.write('\n')
    f.write('south')
    f.close()
    with settings(warn_only=True):
        local('cp example_project/south_settings.py example_project/settings.py')
    #The settings have already been imported so we need to manually add south for testing
    env.INSTALLED_APPS = env.INSTALLED_APPS + ['south']
    #Add a requirements file 
    print "Test that a simple migration passes"
    deploy()
    activate()    

def test_deploy():
    print "TESTING DEPLOY"
    deploy_teardown()
    #with show('debug'):
    deploy()
    activate()
    
    print "RUN AGAIN"
    deploy()
    
    
   
def test_parse_project_version():
    """
    Test the project version
    """
    v = _parse_project_version('0.1')
    env.project_version = ''
    assert v == '0.1'
    v = _parse_project_version('0.1.0.1')
    env.project_version = ''
    assert v == '0.1'
    v = _parse_project_version('0.1 alpha')
    env.project_version = ''
    assert v =='0.1-alpha'
    v = _parse_project_version('0.1a 1234')
    env.project_version = ''
    assert v == '0.1a'
    v = _parse_project_version('0.1-alpha')
    env.project_version = ''
    assert v == '0.1-alpha'
    v = _parse_project_version('0.1 rc1 1234')
    env.project_version = ''
    assert v == '0.1-rc1'
    v = _parse_project_version('0.1.0rc1')
    env.project_version = ''
    assert v == '0.1.0rc1'
    v = _parse_project_version('0.1.1 rc2')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1.rc2.1234')
    env.project_version = ''
    assert v == '0.1.1.rc2'
    v = _parse_project_version('0.1.1-rc2.1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1-rc2-1234')
    env.project_version = ''
    assert v == '0.1.1-rc2'
    v = _parse_project_version('0.1.1 rc2 1234')
    assert v ==  '0.1.1-rc2'  
    