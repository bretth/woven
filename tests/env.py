
from fabric.api import *
from fabric.state import env

from woven.environment import _root_domain, _parse_project_version
from woven.environment import set_env, server_state, set_server_state


def setup():
    sudo('rm -rf /var/local/woven')

def teardown():
    sudo('rm -rf /var/local/woven')
    
def test_env_set_env():
    print "TEST SET ENV"
    set_env()

def test_env_server_state():
    with settings(host_string='root@192.168.188.10:22',user='root',password='root'):
        setup()
        sudo('rm -rf /var/local/woven')
        #test
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
    print v
    v = _parse_project_version('dog')
    print v

def test_env_root_domain():
    #In the event of noinput, the domain will default to example.com
    domain = _root_domain()
    print domain
    assert domain == 'example.com'