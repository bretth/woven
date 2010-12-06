"""
Tests the decorators.py module
"""

from fabric.api import settings, sudo

from woven.decorators import run_once_per_node, run_once_per_version

H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def teardown():
    with settings(host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        sudo('rm -rf /var/local/woven')

def test_dec_run_once_per_node():
    teardown()
    
    @run_once_per_node
    def test_func():
        return 'some'
    
    with settings(host=H, host_string=HS,user=R,password=R,project_fullname='example-0.1'):
        assert test_func() == 'some'
        r = test_func()
        assert not r
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        assert test_func()
    
    teardown()

def test_dec_run_once_per_version():
    teardown()
    
    @run_once_per_version
    def test_func():
        return 'some'
    
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.1'):
        assert test_func() == 'some'
    with settings(host=H,host_string=HS,user=R,password=R,project_fullname='example-0.2'):
        r=test_func()
        assert r
        #run a second time
        assert not test_func()
        
    teardown()
    