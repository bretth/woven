Woven
========

* utilizes Pip, Virtualenv, Fabric and Django templates to simplify deployment making *release early and often* a reality.

* provides six Django commands/functions; ``setupnode``, ``deploy``, ``patch``, ``activate``, ``bundle``, ``startsites``
    
* provides a standard Apache & Nginx webserver configuration that you can change as required.
    
* enables you to define custom Ubuntu etc configuration files in your project

* enable you to define roles for your servers with combinations of Ubuntu packages
    
* integrates into standard Fabric fabfile.py scripts as projects grow.
    
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

To use Woven you must define a minimal :ref:`setup.py` and have root access to an Ubuntu Server host >= 9.10

Woven provides six management commands for your Django project:

``setupnode``, ``deploy``, ``patch``, ``activate``, ``bundle``, ``startsites``

You can walk through some of the commands in a simple example django project :doc:`tutorial` or read the :doc:`commands` docs. You'll also want to have a look at the :doc:`settings` and the project :doc:`conventions`.  

Integrating with Fabric
=======================

Woven is just fabric. To integrate with your own fabfiles you can do:

::

    import os
    from woven.api import set_env
    #or
    
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

Development
===========

The core highlevel functions setupnode, deploy, patch, bundle, and activate will not change, but some other parts of the api may still change between versions. I am aiming to release a beta version sometime after the release of Fabric 1.0.

Testing
--------
Fabric doesn't appear to be compatible with standard python tests. Instead woven stores tests in a fabfile.py in the tests directory.

Individual tests are split across multiple modules corresponding to the module they are testing.

Tests require a vm to be setup with ``root`` login and password ``root`` on 192.168.188.10

Tests can be run by ``fab test`` to run all tests or ``fab test_[modulename]`` to run all tests in the given test module (eg ``fab test_env``), or ``fab [full_test_name]`` to run an individual test from any test module.

Contact
=======

The woven project is hosted on github at http://github.com/bretth/woven. Feature requests and bug reports are welcome.

You can contact me at brett at haydon dot id dot au

