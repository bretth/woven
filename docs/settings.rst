
Settings 
========

Woven has a number of configuration options that can be set in your project's
Django settings.py. They are all optional.

::

    #List of hoststrings to setup on as per Fabric.
    HOSTS = [] #eg ['woven@example.com','example.com','10.0.0.1']
    #You can group collections of servers instead of HOSTS as per fabric
    ROLEDEFS = {} #This would be used instead of HOSTS  eg {'staging':['woven@example.com']}
    #The ssh port to be setup. We change the port for security
    HOST_SSH_PORT = 10022 #default
    #User can be defined here instead of in the hosts/roledefs
    HOST_USER = ''
    #Since password login will normally be disabled you can define it here
    #for just ssh key security per host
    HOST_PASSWORD = ''
    
    #As per fabric KEY_FILENAME option to specify a path to an ssh key to use
    SSH_KEY_FILENAME  = ''
    
    #The first setup task is usually disabling the default root account and changing the ssh port.
    ROOT_USER = 'root', #optional - mostly the default administrative account is root
    DISABLE_ROOT = False, #optional - disable the default administrative account
    ROOT_PASSWORD = '', #optional - blank by default
    #The default ssh port, prior to woven changing it. Defaults to 22
    DEFAULT_SSH_PORT = 22 #default
    DISABLE_SSH_PASSWORD = #optional - setting this to true will disable password login and use ssh keys only.
    #Firewall rules (note HOST_SSH_PORT/tcp is always allowed)
    ENABLE_UFW = True #default - setting this to false will disable UFW
    UFW_RULES = [] #default eg 'allow 5432/tcp'
    ROLE_UFW_RULES = {} # eg {'postgresql':['allow 5432/tcp']}
    
    #The default ubuntu packages that are setup. It is NOT recommended you overwrite these
    #use ROLE_PACKAGES if you want to define all your packages
    HOST_BASE_PACKAGES = [
            'subversion','git-core','mercurial','bzr', #version control
            'gcc','build-essential', 'python-dev', 'python-setuptools', #build
            'apache2','libapache2-mod-wsgi','nginx', #webservers
            'python-imaging', #pil
            'python-psycopg2','python-mysqldb','python-pysqlite2'] #default database drivers
    
    Put any additional packages here to save overwriting the base_packages 
    HOST_EXTRA_PACKAGES = []
    
    #Role packages give you complete flexibility in defining packages with ROLEDEFS.
    #By default any role that does not have role packages defined installs the HOST_BASE_PACKAGES + EXTRA_PACKAGES instead
    ROLE_PACKAGES = {} #eg ROLE_PACKAGES = {'postgresql':['postgresql']}
        
    #Virtualenv/Pip
    DEPLOYMENT_ROOT = ''# defaults to /home/$USER. 
    DJANGO_REQUIREMENT = '' #defaults to your current django version. A pip requirements string for the version of Django to install
    PIP_REQUIREMENTS = [] # list of text pip requirements files (not pybundles). Defaults to any file in the setup.py directory with `req` prefix
    # Note: Woven will also look for pybundles matching the requirements in the dist directory - you can use the bundle management command to create these.
    
    PROJECT_APPS_PATH = '' #a relative path from the project package directory for any local apps. See also the wsgi template.
    
    #Application media - as per build_static app
    STATIC_URL = '' #by default this is set to the ADMIN_MEDIA_PREFIX
    STATIC_ROOT = '' #by default this gets set to the admin media directory if admin is used
    
    #Database migrations
    MANUAL_MIGRATION = False #Manage database migrations manually


