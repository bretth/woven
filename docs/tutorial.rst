Tutorial
========

A simple django project is the best way to illustrate how to get started with woven (and django)

Starting the project
--------------------

.. Note::

    This first bit doesn't have much to do with woven, and is more about personal preference in setting up your development environment but lets walk through *one* way you can get setup. For this you probably want pip, virtualenv and virtualenvwrapper installed and working before you can begin.

We're going to create a virtual python environment ``first-django``. You don't need to do this but virtualenv makes it easy to experiment without polluting your system installed packages.

``mkproject first-django``

Activate the env if it isn't already..

``workon first-django``

Finally create a first-django distribution directory if mkproject hasn't already created one.

Okay lets get into woven.

Installing the packages
-----------------------

Install woven - making sure it correctly installs in the virtualenv.

``pip install django``
``pip install woven``

It should also install fabric, and paramiko if they aren't already installed.

Creating the distribution and project
--------------------------------------

Create a project distribution and files using woven's ``woven-admin.py`` script. A distribution is all the files including media and other data relating to the project whereas the project is just the Django project. We're going to call the distribution something different from the actual project.

``woven-admin.py startproject helloadmin woven@example.com --dist=first-django``

``woven-admin.py`` extends ``django-admin.py`` allowing us to use woven commands without adding woven itself to the ``INSTALLED_APPS`` setting. 

You'll notice that it's a little different from ``django-admin.py startproject`` in that it creates a ``setup.py`` and a few other folders, and merges in the syncdb and creates a default superuser based on the user part of the optional email address (in this case 'woven') or the project name if you want one, though you can skip this behaviour with ``--nosyncdb``. As you'll discover, woven's ethos combines convenience with flexibility. Sometimes you need to get somewhere in a hurry, or just want a project you can throw away after using.

The setup.py is where woven gets your distribution name, project name and project version metadata which is used in deployments, it's just not used to package your project... yet. That will come when it morphs into setup.cfg and uses distutils2.

Woven's alternative to django's ``startproject`` also creates some sensible folders for media, static (app) content, templates, and database, and uses an alternative settings file from the django default. Nothing stopping you from changing it later if you want or you can also use ``startproject -t`` option to specify alternative starting templates for your project.

In the urls.py uncomment the admin lines then at the end of your urls.py we'll add a simple index page.::

   urlpatterns += patterns('django.views.generic.simple',
      (r'^$', 'direct_to_template', {'template': 'index.html'}),
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

To add a package to the PYTHONPATH you would normally install it using setup.py, but since we're developing, link the project folder ``helloadmin`` into your site packages. I recommend these pylink/pyunlink shell scripts: https://gist.github.com/21649. I don't recommend using add2virtualenv since it puts the setup.py in the path.

Change directory into the distribution folder (the one with setup.py in it) and run ``woven-admin.py runserver``, opening http://127.0.0.1:8000/ in your browser.

``woven-admin.py`` doesn't require you to set a DJANGO_SETTINGS_MODULE in the environment (though you can). Instead it infers your settings from the ``setup.py`` project name if you're somewhere under or in the setup.py folder, but you can also use ``--settings`` option as per normal.

If you have done everything right you should now see ``hello admin`` and be able to login to the django admin with the superuser. You're ready to deploy!

Setting up your server
----------------------

Although woven does allow you to scale your deployment to multiple nodes, it doesn't support creating the initial image, so for now you'll need to purchase and startup an Ubuntu virtual machine separately.

Obtain an Ubuntu 10.04 or greater VM on the host of your choice with root and ssh access. For this tutorial I'm going to use a micro instance on Amazon EC2. See http://docs.amazonwebservices.com/AWSEC2/latest/GettingStartedGuide/ for how to get started on EC2.

    1. Create a micro Ubuntu 10.04 x32instance ami-95c694d0 ebs on us-west (or similar) and a woven keypair.
    2. Save the woven.pem key into your distribution folder
    3. ``chmod 400 woven.pem``
    4. Create a security group with ports 22,80,10022 tcp open
    5. Create and associate an elastic IP to the instance

Because django uses ``example.com`` as it's first site, we'll stick with that for this tutorial deployment. In your local ``/etc/hosts`` file add an entry for example.com pointing to the ip address of the ubuntu host (and on osx, run ``dscacheutil -flushcache`` just to be sure).

Just to be sure - check that you can login to your ec2 instance::

    ssh -i woven.pem ubuntu@example.com

Setupnode
---------

Now run setupnode to setup a baseline node for your intended user - in this case woven. The first thing woven will do is setup an additional user and if 'root' is the default user it will be disabled. It will also change the ssh port which is how woven determines that it has been pre-installed.

.. code-block:: bash

    woven-admin.py setupnode -i woven.pem woven@example.com

or for non ec2, just woven-admin.py setupnode woven@example.com
Answer according to your instance. Your root user may vary according to the provider. In our case with ec2 it is `ubuntu`.

.. Note:: 
	
	You might have noticed that setupnode uploads some files to the ubuntu ``etc`` directories. *Your node (host) configuration is stored in your project*. Woven allows you to define your own etc configuration files for ubuntu packages as standard templates in your project. If you want to modify the woven default templates you can copy them from the installed woven package into a woven folder in your projects templates folder like any other django app templates.

You can re-run setupnode at any time to alter your node configuration and update, upgrade and install new debian packages.

Now that your server is setup it's time to deploy our helloadmin project.

Deploy
----------------

*Deploy early. Deploy often.*

Lets collect the static media assets and deploy.

.. code-block:: bash

    woven-admin.py collectstatic 
    woven-admin.py deploy woven@example.com

Deploy sets up a virtual environment on the server and deploys your sqlite3 database, django, and your project and all your dependencies into it. Sqlite3 is the default but again there's nothing stopping you dumping to a file and importing into Postgres or Mysql.

Everything in a deployment is versioned right down to the web configuration files. The only thing that isn't versioned is your database and MEDIA_ROOT. If you get errors, from misconfiguration or package installs, you can just fix your issue and run it again until it completes and activates your environment.

.. Note::
   
   Versions are critical to woven, and how woven differs from most deployment tools. Woven deploys a separate virtualenv just like the one we created earlier for *each* version of your distribution. This means you don't destroy an existing working environment when you deploy a new version. You could use this feature to test different features, or simply to rollback from a failed release. Not that you'll ever have a failed release. Ever.

You'll also notice woven has created a pip ``requirements.txt`` file and a ``sitesettings`` folder with a setting file inside. Requirements are your pip requirements for the project. The sitesettings.settings.py will import and override your local settings file on the node. 

Patch
------

Of course mistakes are made, but to avoid stupidity and overwriting a working installation you cannot re-deploy the same version of your project with deploy (though the ``--overwrite`` option will do the trick if you're desperate). To get around having to deploy a new version for small changes you can run:

.. code-block:: bash

    woven-admin.py patch woven@example.com
    
This will update existing files in your project, media and webserver configurations. It won't delete any files or update any dependencies. To update dependencies to a new library version you should increase your setup.py version and re-run deploy.

Patch can also just upload a specific part of your project using a subcommand. For example to just patch your webconf files:

.. code-block:: bash

    woven-admin.py patch webconf woven@example.com 

The different subcommands are ``project|static|media|templates|webconf``

Where to now
------------

If you want to work directly on the server (perhaps you need to debug something in staging) you can ``ssh woven@example.com -p10022`` into your host and type::

    workon helloadmin
    
This will use virtualenvwrapper to activate your current virtualenv and drop you into the project sitesettings manage.py directory. A convenience manage.py is provided to run ./manage.py from there on the first site.

Of course installing packages from a requirements file can be problematic if pypi or a particular site is down . Make use of the ``woven-admin.py bundle`` command. This will use pip to bundle all the requirements into a dist folder in the distribution for deploy command to use. 

We also haven't covered in this tutorial features such as roles, integrated South migrations and multi-site creation with ``startsites``. Have a read of the woven django management :doc:`commands` for more.
