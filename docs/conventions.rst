Conventions 
===========

Woven will use the following conventions to layout your project on the target host, and uses some basic coventions on the local development machine.

In the following examples we are deploying a distribution ``example_distribution`` with the django project ``example_project`` to a site ``example.com``

.. _setup.py:

Setup.py
--------

A setup file must be defined in your distribution.

**setup.py**::

    from distutils.core import setup
    
    setup(name='example_distribution', #This is what your virtualenvs will be called
          version='0.1',
          packages=['example_project'],
          )

Project Development Layout
--------------------------

While woven tries to be agnostic about your project layout there are some conventions.

::
    
    distribution folder
        |--dist (a dist folder will be created if you *bundle* requirements)
        |    |--requirements.zip (bundle will zip up python packages here with matching req*.txt file name)
        |--setup.py (a minimal setup.py is required with name, version, and packages defined)
        |--requirements.txt (a requirements.txt will be created if one doesn't exist)
        |--example_project (the standard django startproject)
                 |--__init__.py
                 |--deploy.py (optional hooks for custom setupnode or deploy functions)
                 |--manage.py
                 |--settings.py (global settings & local development settings)
                 |--urls.py
                 |--sitesettings (will be created if it doesn't exist)
                         |--__init__.py
                         |--settings.py (the sites specific setting overrides)
                         |--subdomain_settings.py (a site subdomain with the same SITE_ID)
                         |--manage.py (a convenience for running on node against site settings.py)
                 |--local_apps (you can define an optional PROJECT_APPS_PATH in settings that will hold apps and be in site-packages path on deployment)
                         |--app1
                              |--deploy.py (hooks can be at app level as well)
                         |--...
        |--media (actual location as defined in settings)
        |   |--(any user content here)
        |--static  (actual location as defined in settings)
        |   |--(any application media here)
        |--templates (actual location as defined in settings)
            |  #woven comes with a number of default templates in the distribution
            |  #you can copy them and override them in your template directory.
            |--woven 
                 |--etc (optional - copy and override from woven package)
                     |--apache2
                         |--ports.conf
                     |--init.d
                         |--nginx
                     |--nginx
                         |--nginx.conf 
                         |--proxy.conf
                     |--ufw
                         |--applications.d
                             |--woven_project (optional - see notes*)
                     |--ssh
                         |--sshd_config
                 |--django-apache-template.txt (sites conf)          
                 |--django-wsgi-template.txt 
                 |--maintenance.html (for when your site is being deployed)
                 |--nginx-template.txt (sites conf)
                 |--requirements.txt
                 |--sitesettings.txt (default sitesetting)
                 |--ufw.txt (ssh firewall rules)
                 |--ufw-woven_project.txt (project firewall rules)
            |--[template.html] (global projecttemplates here)


**Notes:**

*etc templates*

Templates in the etc folder are uploaded using the following rules:

- templates are uploaded from the project directory first, and if they don't exist the woven package installed templates as per the standard django template loader

- If an etc package subdirectory exists on the node (eg apache2), all templates in the folder are uploaded.

- If an etc subdirectory is not package related (eg init.d) the template will only be uploaded to overwrite an existing template.

etc templates are uploaded if the template has changed or if the packages on the node change.

*UFW firewall rules*

UFW can use app templates defined in the `/etc/ufw/applications.d` directory. Woven uploads `ufw.txt` as `woven` in this directory to set the SSH firewall rules. 

A firewall rule for all nodes can be defined at UFW_RULES or exclusively for a role at ROLE_UFW_RULES. A rule is something like `allow 5432/tcp`. See UFW documentation for rule syntax. Removing a rule will delete it from the firewall next time setupnode is run. 

Project Deployment Layout
-------------------------

Within the root folder on the node are the following::

   ~/.package_cache
   ~/.staging (all rsynced files are staged here before copying to final destination for network efficiency)
   ~/.pip (pip installation logs)
    |  |--cache (Pip will cache packages here)
    |  |--src (pip will store any source repositories here)
   ~/--database (for sqlite if it is used)
    |   |--example_project.db (will always be deployed as the [project-name].db)
    |--env (The root directory for all virtual environments)
        |--example_distribution (symlink to the current virtualenv version)
        |--example_distribution-0.1 (The virtualenv root for this version)
            |--bin
            |--dist
                 |--requirements.pybundle
            |--include 
            |--lib
            |--project
                |--example_project (package directory - symlinked to site-packages)
                    |--manage.py (your development manage.py)
                    |--settings.py (global & dev specific settings)
                    |--sitesettings (site local setting files)
                            |--__init__.py 
                            |--manage.py (you run this on the node)
                            |--settings.py (primary settings file for nodes)
            |--templates (your project templates go here)
            |--static (admin and other app media)
            |--wsgi (web server scripts go here including modwsgi python file)
                 |--settings.wsgi (for modwsgi)
       |--example_distribution-0.2 (next release version - as above)
    ...
    |--log (symlinks to /var/log)
    | Another media directory for files that in the user domain (MEDIA_URL) rather than required for the application
    |--public  (for single domain deployments any project media goes here if you are hosting media locally)
 
    
Apache & Nginx Configuration files
----------------------------------

/etc/apache2/sites-available/
By convention the configuration file will be saved using the domain name as follows.

/etc/apache2/sites-available/example_com-0.1.conf

Nginx for media is done the same way

Server-side State
---------------------

Woven keeps track of server state and other housekeeping functions using the

`/var/local/woven/` directory

Currently state is stored as a filename with or without content.

Backups of configuration files are stored at

`/var/local/woven-backup`
