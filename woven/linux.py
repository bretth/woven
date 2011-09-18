"""
Replaces the ubuntu.py module with more generic linux functions.
"""
#To implement different backends we'll either
#split out functions into function and _backend_functions
#or if the difference is marginal just use if statements
import os, socket, sys
import getpass

from django.utils import importlib

from fabric.state import  _AttributeDict, env, connections
from fabric.context_managers import settings, hide
from fabric.operations import prompt, run, sudo, get, put
from fabric.contrib.files import comment, uncomment, contains, exists, append, sed
from fabric.contrib.console import confirm
from fabric.network import join_host_strings, normalize

from woven.deployment import _backup_file, _restore_file, deploy_files, upload_template
from woven.environment import server_state, set_server_state, get_packages

def _get_template_files(template_dir):
    etc_dir = os.path.join(template_dir,'woven','etc')
    templates = []
    for root, dirs, files in os.walk(etc_dir):
        if files:
            for f in files:
                if f[0] <> '.':
                    new_root = root.replace(template_dir,'')
                    templates.append(os.path.join(new_root,f))

    return set(templates)

def add_repositories():
    """
    Adds additional sources as defined in LINUX_PACKAGE_REPOSITORIES.

    """
    if not env.overwrite and env.LINUX_PACKAGE_REPOSITORIES == server_state('linux_package_repositories'): return
    if env.verbosity:
        print env.host, "UNCOMMENTING SOURCES in /etc/apt/sources.list and adding PPAs"
    if contains(filename='/etc/apt/sources.list',text='#(.?)deb(.*)http:(.*)universe'):

        _backup_file('/etc/apt/sources.list')
        uncomment('/etc/apt/sources.list','#(.?)deb(.*)http:(.*)universe',use_sudo=True)
    install_package('python-software-properties')
    for p in env.LINUX_PACKAGE_REPOSITORIES:
        sudo('add-apt-repository %s'% p)
        if env.verbosity:
            print 'added source', p
    set_server_state('linux_package_repositories',env.LINUX_PACKAGE_REPOSITORIES)

def add_user(username='',password='',group='', site_user=False):
    """
    Adds the username
    """
    if group: group = '-g %s'% group
    if not site_user:
        run('echo %s:%s > /tmp/users.txt'% (username,password))
    if not site_user:
        sudo('useradd -m -s /bin/bash %s %s'% (group,username))
        sudo('chpasswd < /tmp/users.txt')
        sudo('rm -rf /tmp/users.txt')
    else:
        sudo('useradd -M -d /var/www -s /bin/bash %s'% username)
        sudo('usermod -a -G www-data %s'% username)    

def change_ssh_port():
    """
    For security woven changes the default ssh port.
    
    """
    host = normalize(env.host_string)[1]

    after = env.port
    before = str(env.DEFAULT_SSH_PORT)
    

    host_string=join_host_strings(env.user,host,before)
    with settings(host_string=host_string, user=env.user):
        if env.verbosity:
            print env.host, "CHANGING SSH PORT TO: "+str(after)
        sed('/etc/ssh/sshd_config','Port '+ str(before),'Port '+str(after),use_sudo=True)
        if env.verbosity:
            print env.host, "RESTARTING SSH on",after

        sudo('/etc/init.d/ssh restart')
        return True

def disable_root():
    """
    Disables root and creates a new sudo user as specified by HOST_USER in your
    settings or your host_string
    
    The normal pattern for hosting is to get a root account which is then disabled.
    
    returns True on success
    """
    
    def enter_password():
        password1 = getpass.getpass(prompt='Enter the password for %s:'% sudo_user)
        password2 = getpass.getpass(prompt='Re-enter the password:')
        if password1 <> password2:
            print env.host, 'The password was not the same'
            enter_password()
        return password1

    (olduser,host,port) = normalize(env.host_string)
 
    if env.verbosity and not (env.HOST_USER or env.ROLEDEFS):
    
        print "\nWOVEN will now walk through setting up your node (host).\n"

        if env.INTERACTIVE:
            root_user = prompt("\nWhat is the default administrator account for your node?", default=env.ROOT_USER)
        else: root_user = env.ROOT_USER
        if env.user <> 'root': sudo_user = env.user
        else: sudo_user = ''
        if env.INTERACTIVE:
            sudo_user = prompt("What is the new or existing account you wish to use to setup and deploy to your node?", default=sudo_user)
           
    else:
        root_user = env.ROOT_USER
        sudo_user = env.user
        

    original_password = env.get('HOST_PASSWORD','')
    
    host_string=join_host_strings(root_user,host,str(env.DEFAULT_SSH_PORT))
    with settings(host_string=host_string, key_filename=env.key_filename, password=env.ROOT_PASSWORD):
        if not contains('/etc/group','sudo',use_sudo=True):
            sudo('groupadd sudo')

        home_path = '/home/%s'% sudo_user
        if not exists(home_path):
            if env.verbosity:
                print env.host, 'CREATING A NEW ACCOUNT WITH SUDO PRIVILEGE: %s'% sudo_user
            if not original_password:

                original_password = enter_password()
            
            add_user(username=sudo_user, password=original_password,group='sudo')

        #Add existing user to sudo group
        else:
            sudo('adduser %s sudo'% sudo_user)
        #adm group used by Ubuntu logs
        sudo('usermod -a -G adm %s'% sudo_user)
        #add user to /etc/sudoers
        if not exists('/etc/sudoers.wovenbak',use_sudo=True):
            sudo('cp -f /etc/sudoers /etc/sudoers.wovenbak')
        sudo('cp -f /etc/sudoers /tmp/sudoers.tmp')
        append('/tmp/sudoers.tmp', "# Members of the sudo group may gain root privileges", use_sudo=True)
        append('/tmp/sudoers.tmp', "%sudo ALL=(ALL) NOPASSWD:ALL",  use_sudo=True)
        sudo('visudo -c -f /tmp/sudoers.tmp')
        sudo('cp -f /tmp/sudoers.tmp /etc/sudoers')
        sudo('rm -rf /tmp/sudoers.tmp')
        if env.key_filename:
            sudo('mkdir -p /home/%s/.ssh'% sudo_user)
            sudo('cp -f ~/.ssh/authorized_keys /home/%s/.ssh/authorized_keys'% sudo_user)
            sudo('chown -R %s:sudo /home/%s/.ssh'% (sudo_user,sudo_user))
            
    env.password = original_password

    #finally disable root
    host_string=join_host_strings(sudo_user,host,str(env.DEFAULT_SSH_PORT))
    with settings(host_string=host_string):
        if sudo_user <> root_user and root_user == 'root':
            if env.INTERACTIVE:
                d_root = confirm("Disable the root account", default=True)
            else: d_root = env.DISABLE_ROOT
            if d_root:
                if env.verbosity:
                    print env.host, 'DISABLING ROOT'
                sudo("usermod -L %s"% 'root')

    return True

def install_package(package):
    """
    apt-get install [package]
    """
    #install silent and answer yes by default -qqy
    sudo('apt-get install -qqy %s'% package, pty=True)
    
def install_packages():
    """
    Install a set of baseline packages and configure where necessary
    """

    if env.verbosity:
        print env.host, "INSTALLING & CONFIGURING NODE PACKAGES:"
    #Get a list of installed packages
    p = run("dpkg -l | awk '/ii/ {print $2}'").split('\n')
    
    #Remove apparmor - TODO we may enable this later
    if env.overwrite or not server_state('apparmor-disabled') and 'apparmor' in p:
        with settings(warn_only=True):
            sudo('/etc/init.d/apparmor stop')
            sudo('update-rc.d -f apparmor remove')
            set_server_state('apparmor-disabled')

    #The principle we will use is to only install configurations and packages
    #if they do not already exist (ie not manually installed or other method)
    env.installed_packages[env.host] = []
    role = env.role_lookup[env.host_string]
    packages = get_packages()
    for package in packages:
        if not package in p:
            install_package(package)
            if env.verbosity:
                print ' * installed',package
            env.installed_packages[env.host].append(package)
    if env.overwrite or env.installed_packages[env.host]: #always store the latest complete list
        set_server_state('packages_installed', packages)
        env.installed_packages[env.host] = packages

    if env.overwrite and 'apache2' in env.installed_packages[env.host]: 
            #some sensible defaults -might move to putting this config in a template
            sudo("rm -f /etc/apache2/sites-enabled/000-default")
            sed('/etc/apache2/apache2.conf',before='KeepAlive On',after='KeepAlive Off',use_sudo=True, backup='')
            sed('/etc/apache2/apache2.conf',before='StartServers          2', after='StartServers          1', use_sudo=True, backup='')
            sed('/etc/apache2/apache2.conf',before='MaxClients          150', after='MaxClients          100', use_sudo=True, backup='')
            for module in env.APACHE_DISABLE_MODULES:
                sudo('rm -f /etc/apache2/mods-enabled/%s*'% module)
    #Install base python packages
    #We'll use easy_install at this stage since it doesn't download if the package
    #is current whereas pip always downloads.
    #Once both these packages mature we'll move to using the standard Ubuntu packages
    if (env.overwrite or not server_state('pip-venv-wrapper-installed')) and 'python-setuptools' in packages:
        sudo("easy_install virtualenv")
        sudo("easy_install pip")
        sudo("easy_install virtualenvwrapper")
        if env.verbosity:
            print " * easy installed pip, virtualenv, virtualenvwrapper"
        set_server_state('pip-venv-wrapper-installed')
    if not contains("/home/%s/.profile"% env.user,"source /usr/local/bin/virtualenvwrapper.sh"):
        append("/home/%s/.profile"% env.user, "export WORKON_HOME=$HOME/env")
        append("/home/%s/.profile"% env.user, "source /usr/local/bin/virtualenvwrapper.sh")

    #cleanup after easy_install
    sudo("rm -rf build")

def lsb_release():
    """
    Get the linux distribution information and return in an attribute dict
    
    The following attributes should be available:
    base, distributor_id, description, release, codename
    
    For example Ubuntu Lucid would return
    base = debian
    distributor_id = Ubuntu
    description = Ubuntu 10.04.x LTS
    release = 10.04
    codename = lucid
    
    """
    
    output = run('lsb_release -a').split('\n')
    release = _AttributeDict({})
    for line in output:
        try:
            key, value = line.split(':')
        except ValueError:
            continue
        release[key.strip().replace(' ','_').lower()]=value.strip()
   
    if exists('/etc/debian_version'): release.base = 'debian'
    elif exists('/etc/redhat-release'): release.base = 'redhat'
    else: release.base = 'unknown'
    return release
    
def port_is_open():
    """
    Determine if the default port and user is open for business.
    """
    with settings(hide('aborts'), warn_only=True ):
        try:
            if env.verbosity:
                print "Testing node for previous installation on port %s:"% env.port
            distribution = lsb_release()
        except KeyboardInterrupt:
            if env.verbosity:
                print >> sys.stderr, "\nStopped."
            sys.exit(1)
        except: #No way to catch the failing connection without catchall? 
            return False
        if distribution.distributor_id <> 'Ubuntu':
            print env.host, 'WARNING: Woven has only been tested on Ubuntu >= 10.04. It may not work as expected on',distribution.description
    return True

def restrict_ssh(rollback=False):
    """
    Set some sensible restrictions in Ubuntu /etc/ssh/sshd_config and restart sshd
    UseDNS no #prevents dns spoofing sshd defaults to yes
    X11Forwarding no # defaults to no
    AuthorizedKeysFile  %h/.ssh/authorized_keys

    uncomments PasswordAuthentication no and restarts sshd
    """

    if not rollback:
        if server_state('ssh_restricted'):
            return False

        sshd_config = '/etc/ssh/sshd_config'
        if env.verbosity:
            print env.host, "RESTRICTING SSH with "+sshd_config
        filename = 'sshd_config'
        if not exists('/home/%s/.ssh/authorized_keys'% env.user): #do not pass go do not collect $200
            print env.host, 'You need to upload_ssh_key first.'
            return False
        _backup_file(sshd_config)
        context = {"HOST_SSH_PORT": env.HOST_SSH_PORT}
        
        upload_template('woven/ssh/sshd_config','/etc/ssh/sshd_config',context=context,use_sudo=True)
        # Restart sshd
        sudo('/etc/init.d/ssh restart')
        
        # The user can modify the sshd_config file directly but we save
        proceed = True
        if not env.key_filename and (env.DISABLE_SSH_PASSWORD or env.INTERACTIVE) and contains('/etc/ssh/sshd_config','#PasswordAuthentication no',use_sudo=True):
            print "WARNING: You may want to test your node ssh login at this point ssh %s@%s -p%s"% (env.user, env.host, env.port)
            c_text = 'Would you like to disable password login and use only ssh key authentication'
            proceed = confirm(c_text,default=False)
    
        if not env.INTERACTIVE or proceed or env.DISABLE_SSH_PASSWORD:
            #uncomments PasswordAuthentication no and restarts
            uncomment(sshd_config,'#(\s?)PasswordAuthentication(\s*)no',use_sudo=True)
            sudo('/etc/init.d/ssh restart')
        set_server_state('ssh_restricted')
        return True
    else: #Full rollback
        _restore_file('/etc/ssh/sshd_config')
        if server_state('ssh_port_changed'):
            sed('/etc/ssh/sshd_config','Port '+ str(env.DEFAULT_SSH_PORT),'Port '+str(env.HOST_SSH_PORT),use_sudo=True)
            sudo('/etc/init.d/ssh restart')
        sudo('/etc/init.d/ssh restart')
        set_server_state('ssh_restricted', delete=True)
        return True

def set_timezone(rollback=False):
    """
    Set the time zone on the server using Django settings.TIME_ZONE
    """
    if not rollback:
        if contains(filename='/etc/timezone', text=env.TIME_ZONE, use_sudo=True):
            return False
        if env.verbosity:
            print env.host, "CHANGING TIMEZONE /etc/timezone to "+env.TIME_ZONE
        _backup_file('/etc/timezone')
        sudo('echo %s > /tmp/timezone'% env.TIME_ZONE)
        sudo('cp -f /tmp/timezone /etc/timezone')
        sudo('dpkg-reconfigure --frontend noninteractive tzdata')
    else:
        _restore_fie('/etc/timezone')
        sudo('dpkg-reconfigure --frontend noninteractive tzdata')
    return True

def setup_ufw():
    """
    Setup basic ufw rules just for ssh login
    """
    if not env.ENABLE_UFW: return
   
    ufw_state = server_state('ufw_installed')
    if ufw_state and not env.overwrite or ufw_state == str(env.HOST_SSH_PORT): return
    #check for actual package
    ufw = run("dpkg -l | grep 'ufw' | awk '{print $2}'").strip()
    if not ufw:
        if env.verbosity:
            print env.host, "INSTALLING & ENABLING FIREWALL ufw"
        install_package('ufw')

    if env.verbosity:
        print env.host, "CONFIGURING FIREWALL ufw"
    #upload basic woven (ssh) ufw app config
    upload_template('/'.join(['woven','ufw.txt']),
        '/etc/ufw/applications.d/woven',
        {'HOST_SSH_PORT':env.HOST_SSH_PORT},
        use_sudo=True,
        backup=False)
    sudo('chown root:root /etc/ufw/applications.d/woven')
    with settings(warn_only=True):
        if not ufw_state:
            sudo('ufw allow woven')
        else:
            sudo('ufw app update woven')
    _backup_file('/etc/ufw/ufw.conf')
        
    #enable ufw
    sed('/etc/ufw/ufw.conf','ENABLED=no','ENABLED=yes',use_sudo=True, backup='')
    with settings(warn_only=True):
        output = sudo('ufw reload')
        if env.verbosity:
            print output
            
    set_server_state('ufw_installed',str(env.HOST_SSH_PORT))
    return

def setup_ufw_rules():
    """
    Setup ufw app rules from application templates and settings UFW_RULES

    """
    
    #current rules
    current_rules = server_state('ufw_rules')
    if current_rules: current_rules = set(current_rules)
    else: current_rules = set([])
    role = env.role_lookup[env.host_string]
    firewall_rules = set(env.firewall_rules[role])
    if not env.overwrite and firewall_rules == current_rules: return
    if env.verbosity:
        print 'CONFIGURING FIREWALL'
    
    delete_rules = current_rules - firewall_rules
    for rule in delete_rules:
        with settings(warn_only=True):
            if env.verbosity:
                print 'ufw delete', rule
            sudo('ufw delete %s'% rule)
    new_rules = firewall_rules - current_rules        
    for rule in new_rules:
        with settings(warn_only=True):
            if env.verbosity:
                print 'ufw', rule
            sudo('ufw %s'% rule)
    set_server_state('ufw_rules',list(firewall_rules))

        
    output = sudo('ufw reload')
    if env.verbosity:
        print output

    

def skip_disable_root():
    return env.root_disabled

def uninstall_package(package):
    """
    apt-get autoremove --purge
    """
    sudo('apt-get autoremove --purge -qqy %s'% package, pty=True)

def uninstall_packages():
    """
    Uninstall unwanted packages
    """
    p = server_state('packages_installed')
    if p: installed = set(p)
    else: return
    env.uninstalled_packages[env.host] = []
    #first uninstall any that have been taken off the list
    packages = set(get_packages())
    uninstall = installed - packages
    if uninstall and env.verbosity:
        print env.host,'UNINSTALLING HOST PACKAGES'
    for p in uninstall:
        if env.verbosity:
            print ' - uninstalling',p
        uninstall_package(p)
        env.uninstalled_packages[env.host].append(p)
    set_server_state('packages_installed',get_packages())
    return

def upgrade_packages():
    """
    apt-get update and apt-get upgrade
    """
    if env.verbosity:
        print env.host, "apt-get UPDATING and UPGRADING SERVER PACKAGES"
        print " * running apt-get update "
    sudo('apt-get -qqy update')
    if env.verbosity:
        print " * running apt-get upgrade"
        print " NOTE: apt-get upgrade has been known in rare cases to require user input."
        print "If apt-get upgrade does not complete within 15 minutes"
        print "see troubleshooting docs *before* aborting the process to avoid package management corruption."
    sudo('apt-get -qqy upgrade')

def upload_etc():
    """
    Upload and render all templates in the woven/etc directory to the respective directories on the nodes
    
    Only configuration for installed packages will be uploaded where that package creates it's own subdirectory
    in /etc/ ie /etc/apache2.
    
    For configuration that falls in some other non package directories ie init.d, logrotate.d etc
    it is intended that this function only replace existing configuration files. To ensure we don't upload 
    etc files that are intended to accompany a particular package.
    """
    role = env.role_lookup[env.host_string]
    packages = env.packages[role]
    #determine the templatedir
    if env.verbosity:
        print "UPLOAD ETC configuration templates"
    if not hasattr(env, 'project_template_dir'):
        #the normal pattern would mean the shortest path is the main one.
        #its probably the last listed
        length = 1000
        env.project_template_dir = ''
        for dir in env.TEMPLATE_DIRS:
            if dir:
                len_dir = len(dir)
                if len_dir < length:
                    length = len_dir
                    env.project_template_dir = dir

    template_dir = os.path.join(os.path.split(os.path.realpath(__file__))[0],'templates','')
    default_templates = _get_template_files(template_dir)
    if env.project_template_dir: user_templates = _get_template_files(os.path.join(env.project_template_dir,''))
    else: user_templates = set([])
    etc_templates = user_templates | default_templates

    context = {'host_ip':socket.gethostbyname(env.host)}
    if env.overwrite or env.installed_packages[env.host]: mod_only = False
    else: mod_only = True
    for t in etc_templates:
        dest = t.replace('woven','',1)
        directory,filename = os.path.split(dest)
        package_name = filename.split('.')[0]
        if directory in ['/etc','/etc/init.d','/etc/init','/etc/logrotate.d','/etc/rsyslog.d']:
            #must be replacing an existing file
            if not exists(dest) and package_name not in packages: continue
        elif directory == '/etc/ufw/applications.d':
            #must be a package name
            if filename not in packages: continue
        elif not exists(directory, use_sudo=True): continue
        uploaded = upload_template(t,dest,context=context,use_sudo=True, modified_only=mod_only)
            
        if uploaded:
            sudo(' '.join(["chown root:root",dest]))
            if 'init.d' in dest: sudo(' '.join(["chmod ugo+rx",dest]))
            else: sudo(' '.join(["chmod ugo+r",dest]))
            if env.verbosity:
                print " * uploaded",dest

def upload_ssh_key(rollback=False):
    """
    Upload your ssh key for passwordless logins
    """
    auth_keys = '/home/%s/.ssh/authorized_keys'% env.user
    if not rollback:
        local_user = getpass.getuser()
        host = socket.gethostname()
        u = '@'.join([local_user,host])
        u = 'ssh-key-uploaded-%s'% u
        if not env.overwrite and server_state(u): return
        if not exists('.ssh'):
            run('mkdir .ssh')
           
        #determine local .ssh dir
        home = os.path.expanduser('~')
        ssh_key = None
        upload_key = True
        ssh_dsa = os.path.join(home,'.ssh/id_dsa.pub')
        ssh_rsa =  os.path.join(home,'.ssh/id_rsa.pub')
        if env.key_filename and env.INTERACTIVE:
                upload_key = confirm('Would you like to upload your personal key in addition to %s'% str(env.key_filename), default=True)
        if upload_key:  
            if os.path.exists(ssh_dsa):
                ssh_key = ssh_dsa
            elif os.path.exists(ssh_rsa):
                ssh_key = ssh_rsa
    
        if ssh_key:
            ssh_file = open(ssh_key,'r').read()
            
            if exists(auth_keys):
                _backup_file(auth_keys)
            if env.verbosity:
                print env.host, "UPLOADING SSH KEY"
            append(auth_keys,ssh_file) #append prevents uploading twice
            set_server_state(u)
        return
    else:
        if exists(auth_keys+'.wovenbak'):
            _restore_file('/home/%s/.ssh/authorized_keys'% env.user)
        else: #no pre-existing keys remove the .ssh directory
            sudo('rm -rf /home/%s/.ssh')
        return    
