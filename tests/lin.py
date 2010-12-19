  
import os

from fabric.api import *
from fabric.contrib.files import uncomment, exists, comment, contains, append, sed
from fabric.state import connections, env
from fabric.network import join_host_strings, normalize

from woven.linux import disable_root, change_ssh_port, port_is_open, setup_ufw
from woven.linux import setup_ufw_rules
from woven.linux import uninstall_packages
from woven.linux import add_repositories

from woven.environment import server_state, set_server_state

H = '192.168.188.10'
HS = 'woven@192.168.188.10:10022'
R = 'woven'


def test_lin_add_repositories():
    add_repositories()
#Step 1 in Server setup process

def teardown_disable_root():
    local('rm -rf .woven')
    with settings(host_string='woven@192.168.188.10:22',user='woven',password='woven'):
        run('echo %s:%s > /tmp/root_user.txt'% ('root','root'))
        sudo('chpasswd < /tmp/root_user.txt')
        sudo('rm -rf /tmp/root_user.txt')
        print "Closing connection %s"% env.host_string
        #print connections
        connections[env.host_string].close()
        try:
            connections['woven@example.com:22'].close()
        except: pass
        original_username = 'woven'
        (olduser,host,port) = normalize(env.host_string)
        host_string=join_host_strings('root',host,'22')
        with settings(host_string=host_string,  password='root'):
            sudo('deluser --remove-home '+original_username)
   

def test_lin_disable_root():

    #automate
    env.DISABLE_ROOT = True
    env.INTERACTIVE = False
    env.HOST_PASSWORD = 'woven'
    env.ROOT_PASSWORD = 'root'
    
    #test
    with settings(host_string='woven@192.168.188.10:22',user='woven',password='woven'):
        disable_root()
        assert exists('/home/woven')
    
        #cleanup - re-enable root
        #teardown_disable_root()
    
def test_lin_change_ssh_port():

    #automate
    env.ROOT_PASSWORD = 'root'
    
    #setup
    host_state_dir = os.path.join(os.getcwd(),'.woven')
    host_state_path = os.path.join(host_state_dir,'example.com')
    if not os.path.exists(host_state_dir):
        os.mkdir(host_state_dir)
    open(host_state_path,'w').close()
    #test
    print "test_change_ssh_port"
    with settings(user='root',password=env.ROOT_PASSWORD):
        change_ssh_port()
    print "test logging in on the new port"
    
    with settings(host_string='root@192.168.188.10:10022',user='root',password=env.ROOT_PASSWORD):
        try:
            run('echo')
        except:
            print "\nTEST: change_ssh_port FAILED"
            return
        print 'CHANGE PASSED'
    with settings(user='root',password=env.ROOT_PASSWORD):
        result = change_ssh_port()
        print result
        assert result  
    #teardown
    with settings(host_string='root@192.168.188.10:10022', user='root',password=env.ROOT_PASSWORD):
        sed('/etc/ssh/sshd_config','Port 10022','Port 22',use_sudo=True)
        sudo('/etc/init.d/ssh restart')
    local('rm -rf .woven')
    return

def test_lin_port_is_open():
    with settings(host_string='root@192.168.188.10:22', user='root',password=env.ROOT_PASSWORD):
        result = port_is_open()
        assert result
        
        sudo("echo 'Debian vers \n \l'> /etc/issue.new")
        sudo('cp -f /etc/issue /tmp/issue.bak')
        sudo('mv -f /etc/issue.new /etc/issue')
        
        result = port_is_open()
        
        sudo ('cp -f /tmp/issue.bak /etc/issue')


#def test_lin_post_install_package():
#    env.installed_packages = ['postgresql','somepackage']
#    post_install_packages()
    
#def test_lin_post_setupnode():
#    post_setupnode()

def test_lin_setup_ufw_rules():
    #first define some rules that was in the settings
    UFW_RULES = ['allow from 127.0.0.1 to any app apache2', 'allow 5432/tcp']

    with settings(packages=p,UFW_RULES=UFW_RULES, host_string=HS,user=R,password=R):
        setup_ufw_rules()
        
        
def test_lin_setup_ufw():
    with settings(host_string='root@192.168.188.10', user='root',password='root'):

        #tests
        env.HOST_SSH_PORT = '22'
        setup_ufw()
        r = sudo('ufw status').strip()
        assert 'woven' in r
        assert 'ALLOW' in r
        
        with settings(warn_only=True):

            sudo('ufw disable')
            sudo('rm -f /etc/ufw/applications.d/woven')
            sudo('rm -f /etc/ufw/applications.d/woven_project')
            apt_get_purge('ufw')
            set_server_state('ufw_installed',delete=True)
        
        #test change port
        print "CHANGE PORT to add 10022"
        env.HOST_SSH_PORT='22,10022'
        setup_ufw()
        r = sudo('ufw status verbose')
        assert '22,10022' in r
        assert '80,443' in r
        
        #test add an allow
        env.UFW_RULES = ['allow 5432/tcp']
        setup_ufw()
        r = sudo('ufw status verbose')
        assert '5432' in r
        
        #teardown
        sudo('ufw disable')
        sudo('rm -f /etc/ufw/applications.d/woven')
        apt_get_purge('ufw')
        set_server_state('ufw_installed',delete=True)

def test_lin_uninstall_packages():
    uninstall_packages()
    
