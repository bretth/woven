from fabric.contrib.files import exists
from fabric.api import sudo, settings

from woven.deployment import _backup_file, _restore_file

H = '192.168.188.10'
HS = 'root@192.168.188.10:22'
R = 'root'

def test_dep_backup_file():
    with settings(hosts=[H],host_string=HS,user=R,password=R):
        sudo('rm -rf /var/local/woven-backup')
        _backup_file('/etc/ssh/sshd_config')
        assert exists('/var/local/woven-backup/etc/ssh/sshd_config')
        sudo('rm -rf /var/local/woven-backup')
        
        
    


