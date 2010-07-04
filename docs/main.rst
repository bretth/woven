

Installation
============

.. include:: ../INSTALL.txt

Getting Started
===============

Woven currently provides three management commands for your Django project:

``setupnode``, ``deploy`` and ``patch``

Others may be added in the future, but for now that's it. They're pretty simple but Lets walk through how they are used to deploy your project.

Setupnode
----------

To use woven add ``woven`` to your ``INSTALLED_APPS`` in your ``settings.py``

Purchase an Ubuntu 10.04 VM on the host of your choice with root and ssh access.

Create a minimal setup.py in the directory above your django project. This is the only additional configuration file that will be required::

    from setuptools import setup
    setup(
        name = "[package]",
        version = "0.1",
        packages = ['package'],
    )

where `package` is the django-admin.py startproject name. Only name and version are
significant to woven.

Run setupnode from your project directory.

.. code-block:: bash

    python manage.py setupnode [ipaddress]

or

.. code-block:: bash

    python manage.py setupnode [user@ipaddress]

where user is the *new* user that will be created (instead of the current client os user).

Lets go through what this actually does:

1. Changes the default ssh port to 10022
2. Creates the new `user` and disables the `root` user
3. Uploads your public ssh-key
4. Restricts ssh login to the ssh-key and adds a few other restrictions
5. Adds additional sources `universe` to sources.list
6. Updates and upgrades your packages
7. Installs UFW firewall
8. Installs a baseline of Ubuntu packages including Apache, Nginx, and mod-wsgi
9. Sets the timezone according to your settings file

Of course not all hosts are the same and no two deployments are alike so have a look
at some of the :doc:`settings` you can use in your Django project.

Woven uses standard Django templates to create configuration files for Apache, Nginx, and ssh.
If you want to modify them you can copy them from the package into a woven folder in your projects templates folder like any other app.

Deploy
----------------

Deploy early. Deploy often.

First configure the usual necessary project settings.py if they're not already done. Here are some notes about the main ones:: 

    # Woven will deploy your default development sqlite3 database onto the host,
    # otherwise it assumes you manage the db externally.
    'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
    'NAME':,

    # Woven treats MEDIA_ROOT as a public directory that might be used for file storage. 
    MEDIA_ROOT 

    # Woven treats ADMIN_MEDIA_PREFIX as application media 
    # this cannot be on the same path as MEDIA_URL
    ADMIN_MEDIA_PREFIX
 
.. note::

    Woven deploys a separate virtual environment and configuration for each significant version of your project. This includes your project and python library dependencies including Django itself. It also includes application media (such as admin), your webserver configuration, and wsgi file. The only thing that doesn't get versioned is MEDIA_ROOT which is where you might store user created media (and file-storage). See :doc:`conventions` for more information about how woven lays out your project on the host.   

Follow the usual django instructions for enabling admin for your site and then run ``python manage.py syncdb``.
Make sure you can login to your default admin site, and if everything is alright it is time to do your first deployment.

.. code-block:: bash

    python manage.py deploy [user@ipaddress]

The first thing it will ask for is the root domain. This is your SITE_ID = 1 domain. You can define it as the first domain in the ``DOMAINS`` list setting in your settings.py.

.. note::

    Make sure your domain server or /etc/hosts file has an entry for the domain (and on osx, run ``dscacheutil -flushcache``).
    
Deploy does the following::

1. For your first deployment it will deploy your sqlite database
2. Create a virtualenv for the project version
3. Install django. By default it will install the current version. You can set a pip requirements string DJANGO_REQUIREMENT in your settings.py if you want svn trunk or some other version
4. Install dependencies from one or more requirement req*.txt files. eg. req1.txt, requirements.txt. If one doesn't exist then it will create one locally and add woven in it by default.
5. Creates a local sitesettings folder and a settings file for your server [root domain].py if it doesn't already exist. You can see how woven lays out your project on the server here.
6. Deploys your project to the virtualenv on the server
7. Deploys your root (shortest path) TEMPLATE_DIR into a templates directory on the server.
8. Deploys admin media or STATIC_ROOT setting (if you use django-staticfiles) into a virtualenv static directory.
9. Deploys anything at MEDIA_ROOT into a non-virtualenv public directory.
10. Deploys your domain wsgi file into a virtualenv wsgi directory as [domain].wsgi
11. Renders your apache and nginx templates and deploys them into the sites-available with the version in the name.
12. Symlinks the webserver conf versions into sites-enabled
13. Stops the webservices
14. Symlinks the project virtualenv version to the active virtualenv.
15. Starts the webservices

.. note::

    Currently the deploy command **does not** do any data/schema migration. Future versions will integrate with south,
    and provide an optional point to do any custom migration.

Patch
------

Of course mistakes are made, and you cannot re-deploy the same significant version. A significant version might be 0.1, 0.1.1 or something like 0.1.0-alpha etc. An insignificant version might be 0.1.0.1 when the last digit is your build number. To get around having to deploy a new version for small changes you can run:

.. code-block:: bash

    python manage.py patch [user@ipaddress]
    
This will update existing files in your project, media and webserver configurations. It won't delete any files or update any dependencies. To update dependencies to a new library version you would need to increase your setup.py version and re-run deploy.

Where to now
------------

SSH into your host and type::

    source workon-[projectname]
    
This will activate your current virtualenv and drop you into the project manage.py directory.

Of course installing packages from a requirements file each version can be slow, especially if you are
downloading the same django version each time. To get around this first set your DJANGO_REQUIREMENT setting to file:///path/to/Django-x.x.x.tar.gz to rsync against a local copy. Next make use of pip ``bundle`` command. ``pip bundle dist/requirements-0.1.pybundle -r requirements.txt`` to bundle all the requirements into a dist directory in project. Woven will look in the dist directory first and install from a bundle with the same name as the requirements file with the current significant version on the end.

Development
===========

At the current version, Woven is under heavy development and may change radically until it gets closer to 1.0,
though the core highlevel functions setupnode, deploy, and patch will not change.

The main feature goals of this project are to:

* allow deployment of Django projects with minimal configuration and using just a minimal setup.py file, your existing project settings.py, and a pip requirements file
* take advantage of a proper setup.py sdist with a ``package`` command that creates bundles and source distributions. (not yet implemented)
* issue arbitrary management commands to hosts ``python manage.py node [command] --host=[user@ipaddress]`` (not yet implemented)
* deploy each significant version of your project and dependencies into a separate virtualenv virtual python environment to allow simple switching/rollback between versions
* integration with Django South for database & data migration (not yet implemented)
* maintainance pages for downtime (not yet implemented)
* allow simple deployment of multi-site projects (not yet implemented)
* allow command usage within a standard Fabric fabfile.py if complex configuration is required
* provide standard django templates for all configuration files such as apache, nginx, mod-wsgi 
* scale out to multi-host multi-site (not yet implemented)
* configure postgresql (not yet implemented)
* setup option for GeoDjango (not yet implemented)
* install any configuraton templates for ubuntu packages in /etc/[package] (not yet implemented).

The woven project is hosted on github at http://github.com/bretth/woven. Feature requests and bug reports are welcome.

