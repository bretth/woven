

Installation
============

.. include:: ../INSTALL.txt

Getting Started
===============

Add ``woven`` to your ``INSTALLED_APPS`` in your ``settings.py``

Purchase an Ubuntu 10.04 VM on the host of your choice with root and ssh access.

Create a minimal setup.py in the directory above your django project.::

    from setuptools import setup
    setup(
        name = "[package]",
        version = "0.1",
        packages = ['package'],
    )

where `package` is the django-admin.py startproject name. Only name and version are
significant to woven.

Run setupserver from your project directory.

.. code-block:: bash

    python manage.py setupnode ipaddress

or

.. code-block:: bash

    python manage.py setupnode user@ipaddress

where user is the *new* user that will be created (instead of the current os user).

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

That's it for now, additional management commands ``deploy``, ``patch``, and ``rollback`` will be added
soon to actually deploy your project to your freshly minted server.

Development
===========

The main goals of this project are to:

* allow deployment of Django projects with minimal configuration and using just a minimal setup.py file, your existing project settings.py, and a pip requirements file
* deploy each significant version of your project and dependencies into a separate virtualenv virtual python environment to allow simple switching/rollback between versions
* integration with Django South for database & data migration
* allow simple deployment of multi-site projects
* allow command usage within a standard Fabric fabfile.py if complex configuration is required
* provide standard django templates for all configuration files such as apache, nginx, mod-wsgi

The woven project is hosted on github at http://github.com/bretth/woven.

