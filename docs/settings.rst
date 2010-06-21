
Settings 
========

Woven has a number of configuration options that can be set in your project's
Django settings.py. They are all optional.

::

    #List of host strings to setup on as per Fabric
    HOSTS = []
    #List of domains that will be deployed on the host. The first is the primary domain
    DOMAINS = []
    #For deploying a staging server (Not Yet Implemented)
    ROLEDEFS = {'staging':['']}
    #The ssh port to be setup. We change the port for security
    HOST_SSH_PORT = 10022 #default
    #User can be defined here instead of in the hosts
    HOST_USER = ''
    #Since password login will normally be disabled you can define it here
    #for just ssh key security per host, but I wouldn't recommend it 
    HOST_PASSWORD = '' 
    
    #The first setup task is usually disabling the default root account and
    #changing the ssh port. If root is already disabled and the port changed
    #we assume the host_string user is already created and has sudo permissions
    
    ROOT_DISABLED = False #default 
    ROOT_PASSWORD = ''
    #The default ssh port, prior to woven changing it. Defaults to 22
    DEFAULT_SSH_PORT = 22 #default
    #Firewall rules (note HOST_SSH_PORT/tcp is always allowed)
    UFW_RULES = ['allow 80/tcp','allow 443/tcp'] #default  
    
    #The default ubuntu packages that are setup. It is NOT recommended you overwrite these
    HOST_BASE_PACKAGES = [
            'unattended-upgrades', #base
            'subversion','git-core','mercurial','bzr', #version control
            'gcc','build-essential', 'python-dev', 'python-setuptools', #build
            'apache2','libapache2-mod-wsgi','nginx', #webservers
            'python-imaging', #pil
            'python-psycopg2','python-mysqldb','python-pysqlite2'] #default database drivers
    
    #Put any additional packages here to save overwriting the base_packages
    HOST_EXTRA_PACKAGES = [] 
        
    #Virtualenv/Pip (Not Yet Implemented)
    NO_SITE_PACKAGES = False 
    
    #Application media - as per build_static app
    STATIC_URL = '' #optional (Not Yet Implemented)
    STATIC_ROOT = '' #optional (Not Yet Implemented)


