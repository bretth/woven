#!/usr/bin/env python
from fabric.state import _AttributeDict

woven_env = _AttributeDict({
'HOSTS':[], #optional - a list of host strings to setup on as per Fabric
'DOMAINS':[], #optional a list of domains that will be deployed on the host. The first is the primary domain
'ROLEDEFS':{'staging':['']}, #optional as per fabric. Staging will be used in deployment
'HOST_SSH_PORT':10022, #optional - the ssh port to be setup
'HOST_USER':'', #optional - can be used in place of defining it elsewhere (ie host_string)
'HOST_PASSWORD':'',#optional

#The first setup task is usually disabling the default root account and changing the ssh port.
#If root is already disabled and the port changed. we assume the host_string user is already created and has sudo permissions

'ROOT_DISABLED': False, #optional - also means the port has been changed to a new port.
'ROOT_PASSWORD':'', #optional - blank by default
'DEFAULT_SSH_PORT':22, #optional - The default ssh port, prior to woven changing it. Defaults to 22
'UFW_DISABLED':False, #optional - If some alternative firewall is already pre-installed
'UFW_RULES':['allow 80/tcp','allow 443/tcp'], #optional - the default firewall rules (note ssh is always allowed)

#The default ubuntu packages that are setup. It is NOT recommended you change these:
'HOST_BASE_PACKAGES':[
        'unattended-upgrades', #base
        'subversion','git-core','mercurial','bzr', #version control
        'gcc','build-essential', 'python-dev', 'python-setuptools', #build
        'apache2','libapache2-mod-wsgi','nginx', #webservers
        'python-paramiko','fabric',
        'python-imaging', #pil
        'python-psycopg2','python-mysqldb','python-pysqlite2'], #default database drivers

#Put any additional packages here 
'HOST_EXTRA_PACKAGES':[], #optional - additional ubuntu packages as required

    
#Virtualenv/Pip
'PIP_REQUIREMENTS':[], # a list of pip requirement and or pybundle files to use for installation
'DJANGO_REQUIREMENT':'Django',#A pip requirements string for the version of Django to install

#Application media
'STATIC_URL':'', #optional
'STATIC_ROOT':'', #optional

})
