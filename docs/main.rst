Woven
========

* utilizes Pip, Virtualenv, Fabric and Django templates to simplify deployment making *release early and often* a reality.

* provides six Django commands/functions; ``setupnode``, ``deploy``, ``patch``, ``activate``, ``bundle``, ``startsites``
    
* provides a standard Apache & Nginx webserver configuration that you can change as required, and includes experimental support for Gunicorn.

* versions your project with virtualenv
    
* enables you to define custom linux etc configuration files in your project

* enable you to define roles for your servers with combinations of linux packages and firewall rules
    
* provides an api for fabfile.py scripts.

* hooks for custom functionality
    
* integrates with South for migrations
    
* basic multi-site multi-db capabilities


**Woven currently doesn't:**

* Create and launch your node from any cloud providers - it just does the setup of a baseline installation with setupnode
    
* bring you beer

Installation
============

.. include:: ../INSTALL.txt

Getting Started
===============

To use Woven you must have root access to a linux host or vm. Woven has currently been tested on Ubuntu >= 10.04.

Woven uses a custom ``woven-admin.py`` script that serves to replace django-admin.py and manage.py in your development environment, and allows you to use woven commands without adding woven to your installed apps.

Run ``woven-admin.py startproject`` which will create a basic django project distribution layout.

Woven provides six management commands for your Django project:

``setupnode``, ``deploy``, ``patch``, ``activate``, ``bundle``, ``startsites``

You can walk through some of the commands in a simple example django project :doc:`tutorial` or read the :doc:`commands` docs. You'll also want to have a look at the :doc:`settings` and the project :doc:`conventions`.  

Integrating with Fabric
=======================

Woven is just fabric. To integrate with your own fabfiles you can do:

::

    import os

    #import any other woven functions you want to use or all of them
    from woven.api import *
    
    #Set the environ for Django if you need to
    #(assumes you have your project on the pythonpath)
    os.environ['DJANGO_SETTINGS_MODULE'] = 'example_project.settings'
    
    #set_env will initialise your env for woven functions and use your settings
    set_env()

    #define your own fabric functions that use woven
    def your_function():
        ...

Custom Hooks
============

Woven provides hooks into the setupnode, deploy, and post package installation commands.

To add custom functionality to a woven deployment create a ``deploy.py`` file in your project or django app, and define any of the following.

Hooks execute in a project, app, woven order of precedence. Only one hook per function will execute. A project scope hook for instance will override the same function at app or provided by woven itself.

Post install package
---------------------

Define a ``def post_install_[package_name]()`` function to run code if the Ubuntu package is installed by woven, and after any /etc configuration is uploaded. For example you might define ``def post_install_postgresql()`` to setup a postgresql database. Replace any dashes or fullstops with underscores to make it a valid python function.

A sample hook is defined in Woven for installing postgresql

Post setupnode
--------------

``def post_setupnode()`` executes at the end of the setupnode process.

Post deploy
-----------

``def post_deploy()`` executes at the end of deployment of your project but prior to activation.

Multiple Sites
==============

Woven creates a user on the node for each SITE_ID. The users will be called ``site_1``, ``site_2`` ... The Apache site templates use process groups to launch modwsgi daemons running as the site user. The settings file gets the current user and dynamically sets the SITE_ID in the settings. In this fashion a single settings file can be used for multiple sites.

Since Django sites uses a SITE_ID rather than a domain to represent the site, it doesn't really know about subdomains, but you might want might make a default admin view of your SITE_ID = 1 at admin.example.com. To accommodate this you can make a settings file called admin_settings.py in the sitesettings folder. You would add a prefix for any other alternative view of the same site using [sub_domain]_settings.py

Development
===========

The core highlevel functions setupnode, deploy, patch, bundle, and activate will not change, but some other parts of the api may still change between versions. I am aiming to release a beta version (something less than 1.0) sometime after the release of Fabric 1.0, since Fabric 1.0 will currently break Woven due to backwards incompatabilities. After that time Woven will depend on Fabric >= 1.0. 

Future Goals
------------

* I would like to see other ways of serving django behind nginx implemented. Ubuntu 11.04 will ship with a nginx that doesn't need to be compiled to use uwsgi, so that will be a good time to add support for it.
* Although it's currently tested on Ubuntu, I'm happy to accept patches or feedback to make it work on debian based distro's or other linux distributions.
* The future is distutils2. I actually think the 1.0 version of woven should make full use of the new packaging system and metadata. When packaging no longer sucks, I can simplify woven to leverage it, and it has implications for django project conventions. I'll be looking for distutils2 to move to beta before I begin to develop for it.

Testing
--------
Woven stores tests in a fabfile.py in the tests directory. The tests are pretty incomplete at this time.

Individual tests are split across multiple modules corresponding to the module they are testing.

Tests require a vm to be setup with ``root`` login and password ``root`` on 192.168.188.10

Tests can be run by ``fab test`` to run all tests or ``fab test_[modulename]`` to run all tests in the given test module (eg ``fab test_env``), or ``fab [full_test_name]`` to run an individual test from any test module.

Contact
=======

The woven project is hosted on github at http://github.com/bretth/woven. Feature requests and bug reports are welcome.

You can contact me at brett at haydon dot id dot au

