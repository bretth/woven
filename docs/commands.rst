Management Commands
===================

Commands that run on a node (host) require a hoststring, role or have HOSTS or ROLEDEFS defined in your settings.

As per fabric a hoststring can be username@hostname, or use just the hostname or ip address. If no username is defined then woven will use the current user or that set in settings.HOST_USER. You never need to set the port. It will always use port 10022 though another port can be defined using the HOST_SSH_PORT setting.

A common and recommended deployment pattern is to separate out staging servers from production servers. To do this in woven you would define your hoststrings in the ROLEDEFS settings (like fabfile roledefs). For example to have one staging server and two production servers you could define::
    
    ROLEDEFS = {'staging':['user@192.168.188.10'], 'production':['user@host1.example.com', user@host2.example.com]}
    
You would then use the role in place of the hoststring e.g. ``python manage.py deploy staging``

setupnode
---------

Setup a baseline Ubuntu server ready for deployment

Basic Usage::

``python manage.py setupnode [hoststring]``


bundle
------

Pip bundle your requirements into .pybundles for efficient deployment

``python manage.py bundle``


deploy
------

Deploy your project to a host run syncdb and activate

Basic Usage:

``python manage.py deploy [hoststring]``

*South migration options*

deploy integrates with south if it is installed

``-m --migration`` Specify a specific migration to run

``--fake``  Fake a South migration (see South documentation)

``--nomigration`` Do not migrate

``--manualmigration`` Manage the database migration manually. With this option you can drop out of the current deployment to migrate the database manually, or pause the deployment while migrating in a separate shell. To migrate the database you could login to your host and then run ``workon [yourproject-version]`` to drop into the new versions environment and migrate your database using south, then logout and re-run deploy or continue the existing deploy. 


patch
-----

Patch the current version of your project on hosts and restart webservices
Includes project, web configuration, media, and wsgi but does not pip install

Basic Usage: ``python manage.py patch [subcommand] [hoststring]``

You can just patch a part of the deployment with a subcommand.

The possible subcommands are::

    project, templates, static, public, wsgi, webservers

Example: ``python manage.py patch public woven@host.example.com``


activate
--------

Activate a project version

Usage: ``python manage.py activate [version]``

Examples: ``python manage.py activate 0.1 woven@host.example.com``

node
----

Run a no arguments management command on hosts

Basic Usage: ``python manage.py node [command] [hoststring] --options="[option ...]"``

Examples: ``python manage.py node flush woven@host.example.com --options="--noinput"``




