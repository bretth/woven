
from fabric.api import *
from fabric.state import env

from woven.environment import _root_domain, _parse_project_version
from woven.environment import set_env, server_state, set_server_state
from woven.environment import version_state, set_version_state
H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def setup():
    sudo('rm -rf /var/local/woven')

def teardown():
    sudo('rm -rf /var/local/woven')
    
def test_env_set_env():
    print "TEST SET ENV"
    set_env()

def test_env_server_state():
    with settings(host_string=HS,user=R,password=R):
        setup()
        env.project_fullname = 'example_project-0.1'
        sudo('rm -rf /var/local/woven')
        #test
        set_server_state('example',delete=True)
        set_server_state('example')
        assert server_state('example')
        set_server_state('example',object=['something'])
        state = server_state('example')
        assert state == ['something']
        set_server_state('example',delete=True)
        state = server_state('example')
        assert not state

        teardown()

def test_env_version_state():
    with settings(host_string=HS,user=R,password=R):
        setup()
        env.project_fullname = 'example_project-0.1'
        sudo('rm -rf /var/local/woven')
        #test
        set_version_state('example',delete=True)
        set_version_state('example')
        assert version_state('example')
        set_version_state('example',object=['something'])
        state = version_state('example')
        assert state == ['something']
        state = version_state('example', prefix=True)
        assert state
        
        set_version_state('example',delete=True)
        state = version_state('example')
        assert not state
        teardown()
    
        
def test_env_parse_project_version():
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
    v = _parse_project_version('d.og')
    assert v == 'd.og'
    v = _parse_project_version('dog')
    assert v == 'dog'

def test_env_root_domain():
    with settings(hosts=[H],host_string=HS,user=R,password=R):
        #In the event of noinput, the domain will default to example.com
        domain = _root_domain()
        print domain
        assert domain == 'example.com'