Conventions 
===========

Woven will use the following conventions to layout your project on the target host, and uses some basic coventions on the local development machine

In the following examples we are deploying a distribution ``example_distribution`` with the django project ``example_project`` to a site ``example.com``

.. _setup.py:

Setup.py
--------

A setup file must be defined in your distribution.

**setup.py**::

    from distutils.core import setup
    
    setup(name='example_distribution',
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
                 |--manage.py
                 |--settings.py (global settings & local development settings)
                 |--urls.py
                 |--sitesettings (will be created if it doesn't exist)
                         |--__init__.py
                         |--example_com.py (the site specific setting overrides)
                         |--settings.py (the global sites specific setting overrides)
                         |--manage.py (a convenience for running on node against site settings.py)
                 |--local_apps (you can define an optional PROJECT_APPS_PATH in settings that will hold apps and be in site-packages path on deployment)
                         |--app1
                         |--...
        |--media (actual location as defined in settings)
        |   |--(any user content here)
        |--static  (actual location as defined in settings)
        |   |--(any application media here)
        |--templates (actual location as defined in settings)
            |--template.html (global templates here)
            |--example.com
                |--template.html (site override templates here)


Project Deployment Layout
-------------------------

Within the root folder on the node are the following::

   ~/.package_cache (Pip will cache packages here)
   ~/.staging (all rsynced files are staged here before copying to final destination for network efficiency)
   ~/.pip (pip installation logs)
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
                            |--example_com.py (site local settings)
                            |--manage.py (you run this on the node)
                            |--settings.py (primary settings file for nodes)
            |--templates (your project templates go here)
            |--static (admin and other app media)
            |--wsgi (web server scripts go here including modwsgi python file)
                 |--example_com.py
       |--example_project-0.2 (next release version - as above)
    ...
    |--log (symlinks to /var/log)
    | Another media directory for files that in the user domain (MEDIA_URL) rather than required for the application
    | These would normally be hosted on something like s3, but you may want to host it locally
    |--public  (for single domain deployments any project media goes here if you are hosting media locally)
    |--src (pip will store any source repositories here)
    
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

Currently state is stored as a filename with or without content. This may change.


