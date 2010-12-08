Tutorial
========

A simple project is the best way to illustrate how to get started with woven.

Starting the project
--------------------

This first bit doesn't have much to do with woven, and is more about personal preference in setting up your development environment but lets walk through it anyway. For this you probably want pip, virtualenv and virtualenvwrapper installed and working before you can begin.

We're going to create a virtual python environment hellodjango. You don't need to do this but virtualenv makes it easy to experiment without polluting your system installed packages.

``mkvirtalenv hellodjango --no-site-packages``

Create a ``distribution`` directory in the virtualenv. A distribution usually means a bundle of software configured for release. I'm using the term loosely to be the directory where the django project and *any* related packaged releases will be contained. In python the ``setup.py`` would be found in the distribution directory, and this will be the case here.

``mkdir $WORKON_HOME/hellodjango/distribution``
``cd $WORKON_HOME/hellodjango/distribution``

Activate the env if it isn't already.

``workon hellodjango``

Installing the packages
-----------------------

Install django 1.2.x - making sure it correctly installs in the virtualenv.

``pip install django``

and of course ``pip install woven`` which should also install Woven, Fabric and other dependencies, Paramiko and pycrypto.

Creating the project
-----------------------

Create a django project. 

``django-admin.py startproject helloadmin``

In your distribution folder ``mkdir database media static templates`` folders. Also in your distribution folder create a minimal setup.py::

   from distutils.core import setup
   
   setup(name='hellodjango',
         version='0.1',
         packages=['helloadmin'],
         )

The name is your distribution name which can be different from the name of the project. The first package in packages is *your* django project, and a version is required for deployment.

.. Note::
   
   Versions are critical to woven, and how woven differs from most deployment tools. Woven deploys a separate virtualenv just like the one we created earlier for *each* version of your distribution. This means you don't destroy an existing working environment when you deploy a new version. You could use this feature to test different features, or simply to rollback from a failed release. Not that you'll ever have a failed release. Ever.

Now configure the django settings.py. First up insert the following up the top of your settings.py::

   import os
   PROJECT_ROOT = os.path.split(os.path.realpath(__file__))[0]
   DISTRIBUTION_ROOT = os.path.split(PROJECT_ROOT)[0]

This simply allows you to use dynamic paths if you need to pass your project on to someone else to work on.

The set the database settings.::

    DATABASE_PATH = 
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': DISTRIBUTION_ROOT+'/database/helloadmin.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

Even if you plan to use postgresql or mysql in production sqlite3 is a good place to start because it's super speedy for reads, requires zero configuration, minimal resources and there's nothing stopping you from migrating up to postgresql once you're up and running. 
   
In the settings file we also need to alter the media settings::

    MEDIA_ROOT = DISTRIBUTION_ROOT + '/media/'
    MEDIA_URL = '/media/'
    
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    
.. Note::

    In django 1.3 there is a contrib app called staticfiles that helps organise your application media. STATIC_URL and STATIC_ROOT define your application media including admin media while the MEDIA_ROOT and MEDIA_URL are for user content. In 1.3 you will run the management command collectstatic to collect all your media for deployment. For 1.2, woven will automatically handle admin media for deployment, but the django-staticfiles app can handle collecting application media for you. This tutorial will be updated for 1.3 to include staticfiles.

Alter the template directories::

   TEMPLATE_DIRS = (
      DISTRIBUTION_ROOT+'/templates',
   )

Add ``woven`` to the installed apps and uncomment ``django.contrib.admin``

In the ``urls.py`` make it look like this::

   from django.conf.urls.defaults import *

   # Uncomment the next two lines to enable the admin:
   from django.contrib import admin
   admin.autodiscover()

   urlpatterns = patterns('',
       # Example:
       # (r'^helloadmin/', include('helloadmin.foo.urls')),

       # Uncomment the admin/doc line below to enable admin documentation:
       # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

       # Uncomment the next line to enable the admin:
       (r'^admin/', include(admin.site.urls)),
   )
   
   urlpatterns += patterns('django.views.generic.simple',
      (r'^$', 'django.views.generic.simple.direct_to_template', {'template': 'index.html'}),
   )

Finally in your templates folder create an index.html template file:: 

	<!DOCTYPE html>

	<html>
	<head>
	    <title>Hello admin</title>
	</head>

	<body>
	Hello <a href="/admin/">admin</a>
	</body>
	</html>

From the helloadmin folder run syncdb ``python manage.py syncdb`` to setup the database and then make sure your development environment is working by running ``python manage.py syncdb`` and opening http://127.0.0.1:8000/ in your browser.

If you have done everything right you should now see ``hello admin`` and be able to login to the django admin. You're ready to deploy!

Setting up your server
----------------------

Although woven does allow you to scale your deployment, it currently doesn't support creating the initial image, so for now you'll need to purchase and startup an Ubuntu virtual machine separately.

Obtain an Ubuntu 10.04 or greater VM on the host of your choice with root and ssh access. I'm a big fan of Linode, but any one will do. The smallest Linode 512MB will easily handle Django.

Because django uses ``example.com`` as it's first site, we'll stick with that for deployment. In your local ``/etc/hosts`` file add an entry for example.com pointing to the ip address of the ubuntu host (and on osx, run ``dscacheutil -flushcache``).

Setupnode
---------

Now run setupnode from your manage.py directory.

.. code-block:: bash

    python manage.py setupnode woven@example.com
    
.. Note:: 
	
	You might have noticed that setupnode uploads some files to the ubuntu ``etc`` directories. *Your node (host) configuration is stored in your project*. Woven allows you to define your own etc configuration files for ubuntu packages as standard django templates in your project. If you want to modify the woven default templates you can copy them from the installed woven package into a woven folder in your projects templates folder like any other django app templates.

You can re-run setupnode at any time to alter your node configuration and update and upgrade packages.

Now that your server is setup it's time to deploy our helloadmin project.

Deploy
----------------

*Deploy early. Deploy often.*

Lets deploy our helloadmin project

.. code-block:: bash

    python manage.py deploy woven@example.com

Deploy sets up a virtual environment on the server and deploys your sqlite3 database, django, and your project and all your dependencies into it. Everything is versioned right down to the web configuration files. The only thing that isn't versioned is your database and MEDIA_ROOT. If you get errors, from misconfiguration or package installs, you can just fix your issue and run it again until it completes and activates your environment.

You'll also notice woven has created a pip ``requirements.txt`` file and a ``sitesettings`` folder with some settings files inside. These will inherit and override your local settings file. 

Patch
------

Of course mistakes are made, but to avoid stupidity and overwriting a working installation you cannot re-deploy the same version of your project with deploy (though the ``--overwrite`` option will do the trick if you're desperate). To get around having to deploy a new version for small changes you can run:

.. code-block:: bash

    python manage.py patch woven@example.com
    
This will update existing files in your project, media and webserver configurations. It won't delete any files or update any dependencies. To update dependencies to a new library version you should increase your setup.py version and re-run deploy.

Patch can also just upload a specific part of your project using a subcommand. For example to just patch your webconf files:

.. code-block:: bash

    python manage.py patch webconf woven@example.com 

The different subcommands are ``project|static|media|templates|webconf``

Where to now
------------

If you want to work directly on the server you can SSH into your host and type::

    workon hellodjango
    
This will use virtualenvwrapper to activate your current virtualenv and drop you into the project sitesettings manage.py directory. A convenience manage.py is provided to run manage.py from there on the first site.

Of course installing packages from a requirements file can be problematic if pypi is down. Make use of the ``manage.py bundle`` command. This will use pip to bundle all the requirements into a dist folder in the distribution for deployment. 

We also haven't covered in this tutorial features such as integrated South migrations and multi-site creation with ``startsites``. Have a read of the woven django management :doc:`commands` to get a better feel of the woven commands.
