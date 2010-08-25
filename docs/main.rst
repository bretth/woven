

Installation
============

.. include:: ../INSTALL.txt

Getting Started
===============

Woven provides four core management commands for your Django project:

``setupnode``, ``deploy``, ``patch``, and ``activate``

They're pretty simple and transparent but Lets walk through some of the commands in a real example. For this I'm going to deploy the example feincms project. Why feincms? Well, I like feincms, but a django novice would find it hard to get started out of the box, so it's a good non-trivial example to work with.

Starting the project
--------------------

This first bit doesn't have much to do with woven, and is more about personal preference in  setting up your development environment but lets walk through how I like to do it anyway. You must have git, pip, virtualenv and virtualenvwrapper installed and working before you can begin.

``mkvirtalenv pony-cms --no-site-packages``

I like to make my project directory in the virtualenv.

``mkdir $WORKON_HOME/pony-cms/project``
``cd $WORKON_HOME/pony-cms/project``

Activate the env if it isn't already

``workon pony-cms``

Installing the packages
-----------------------

Install django - making sure it correctly installs in the virtualenv

``pip install django``

Following the Feincms installation docs, it doesn't have a requirements file for pip but we can install the required packages and source repos individually.

``pip install -e git://github.com/matthiask/django-mptt#egg=mptt``
``pip install -e git://github.com/matthiask/feincms.git#egg=feincms``
``pip install pil``
``pip install lxml``
``pip install django-tagging``
``pip install feedparser``
``pip install django-staticfiles``

and finally of course ``pip install woven``

Copy the example project from ``$WORKON_HOME/pony-cms/src/feincms/example`` into your ``project`` folder.

Configuring the project
-----------------------

In the example project update the database settings in the settings.py to the new Django 1.2 format to work with woven.::

    #Old settings
    #DATABASE_ENGINE = 'sqlite3'
    #DATABASE_NAME = os.path.join(os.path.dirname(__file__), 'example.db')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.path.join(os.path.dirname(__file__), 'example.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

   
In the settings file we also need to alter the media settings. This is where django-staticfiles helps smooth out some of the wrinkles with deployment of application media beyond the admin interface, and woven will use the same ``STATIC_ROOT`` and ``STATIC_URL`` settings for deployment.::

    MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media/')
    MEDIA_URL = '/media/'
    STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static/')
    STATIC_URL = '/static/'
    
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    FEINCMS_ADMIN_MEDIA = '/static/feincms/'
    
Note::

    Django-staticfiles neatly splits media into app (STATIC_ROOT) media and MEDIA_ROOT which is the default setting for Django file uploads, so ideally meant for user media. Currently the django development server by design doesn't serve either app media or user media, but unfortunately breaks that rule by then serving admin media as a special "batteries included" exception with it's own prefix. This is a an irritant that Django-staticfiles scratches by treating admin media as just another app, and allowing it all to be served by the development server. See the staticfiles docs for more information.

Add ``staticfiles`` and ``woven`` to your ``INSTALLED_APPS`` setting.

In the example folder run the development server ``python manage.py runserver`` and make sure your development environment is working by browsing to both http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/ the username and password are ``admin`` and ``password``. 

Readying for deployment
-----------------------

Obtain an Ubuntu 10.04 or greater VM on the host of your choice with root and ssh access.

In your local /etc/hosts file add an entry for example.com pointing to the ip address of the ubuntu host (and on osx, run ``dscacheutil -flushcache``).

Create a minimal setup.py in ``project`` directory above ``example``. This is the only configuration that is mandatory for woven::

    from setuptools import setup
    setup(
        name = "[example]",
        version = "0.1",
        packages = ['example'],
    )

Setupnode
---------

Run setupnode from your manage.py directory.

.. code-block:: bash

    python manage.py setupnode woven@example.com
    
This will setup the node and ``woven`` as the user you intend to use to deploy projects. Any standard fabric host string can be used and by default if you just used ``example.com`` it would use the current system user.

The process is fairly verbose by default and you might have noticed that it uploads some files to the ubuntu ``etc`` directories. *Your server (node) configuration is stored in your project*. Woven allows you to define your own etc configuration files for ubuntu as standard django templates in your project.

If you want to modify the woven default templates you can copy them from the installed woven package into a woven folder in your projects templates folder like any other app templates.

Now that your server is setup and the development environment is working it's time to deploy our feincms example project.

Deploy
----------------

*Deploy early. Deploy often.*

.. note::

    Starting with a sqlite3 database is actually a pretty good idea. It's easy to load up to production, performs well for sites that are mostly reads, and if you like you can dump the database and load it into postgresql or mysql when you need *write* scalability or the extra features of an enterprise database.


.. code-block:: bash

    python manage.py deploy woven@example.com


Patch
------

Of course mistakes are made, but you cannot re-deploy the same significant version with deploy. A significant version might be 0.1, 0.1.1 or something like 0.1.0-alpha etc. An insignificant version might be 0.1.0.1 when the last digit is your build number. To get around having to deploy a new version for small changes you can run:

.. code-block:: bash

    python manage.py patch woven@example.com
    
This will update existing files in your project, media and webserver configurations. It won't delete any files or update any dependencies. To update dependencies to a new library version you would need to increase your setup.py version and re-run deploy.

Patch can also just upload a specific part of your project using a subcommand. For example to just patch your webserver conf files:

.. code-block:: bash

    python manage.py patch webconf woven@example.com 

Where to now
------------

If you want to work directly on the server you can SSH into your host and type::

    workon example
    
This will use virtualenvwrapper to activate your current virtualenv and drop you into the project sitesettings manage.py directory. A convenience manage.py and settings.py is provided to run manage.py from there on the first site.

Of course installing packages from a requirements file can be problematic if pypi is down.  To get around this first set your DJANGO_REQUIREMENT setting to file:///path/to/Django-x.x.x.tar.gz to rsync against a local copy. Next make use of  ``manage.py bundle`` command. This will use pip to bundle all the requirements into a dist directory in project. When deploying woven will look in the dist directory first and install from a bundle with the same name as the requirements file.

Have a read of the woven django management :doc:commands to get a better feel of the woven commands. 

Development
===========

At the current version 0.5, Woven has implemented most of it's basic features, and is now aiming to stabilize the api and move from alpha to beta status. There still may be incompatibilities between version 0.5 and 0.6, but will endeavour to provide an upgrade path between versions until the a beta release.  The core highlevel functions setupnode, deploy, patch, and activate will not change.

The woven project is hosted on github at http://github.com/bretth/woven. Feature requests and bug reports are welcome.

You can contact me at brett at haydon dot id dot au

