from fabric.api import *

from woven.webservers import _site_users
from woven.linux import add_user

def test_web_site_users():
    with settings(host_string='root@192.168.188.10:22', user='root',password='root'):
        sudo('userdel site_1')
        users = _site_users()
        assert not users
        #now add a user
        add_user(username='site_1',group='www-data',site_user=True)
        users = _site_users()
        assert users[0] == 'site_1'
        