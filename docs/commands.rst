Management Commands
===================

setupnode
---------

Setup a baseline Ubuntu server ready for deployment

Basic Usage:
``python manage.py setupnode [user]@[hoststring]``

Examples:
``python manage.py setupnode woven@192.168.188.10``
``python manage.py setupnode woven@host.example.com``

bundle
------

Pip bundle your requirements into .pybundles for efficient deployment

``python manage.py bundle``

deploy
------

Deploy your project to a host run syncdb and activate

Basic Usage:
``python manage.py deploy [user]@[hoststring]``

Examples:
``python manage.py deploy woven@192.168.188.10``
``python manage.py deploy woven@host.example.com``

For just the current user
``python manage.py deploy host.example.com``


*South migration options*

deploy integrates with south if it is installed

``-m --migration`` Specify a specific migration to run

``--fake``  Fake a South migration (see South documentation)

``--nomigration`` Do not migrate

``--manualmigration`` Manage the database migration manually. With this option you can drop out of the current deployment to migrate the database manually, or pause the deployment while migrating in a separate shell. To migrate the database you could login to your node and then run ``workon [yourproject-version]`` to drop into the new versions environment and migrate your database using south, then logout and re-run deploy or continue the existing deploy. 


patch
-----

Patch the current version of your project on hosts and restart webservices
Includes project, web configuration, media, and wsgi but does not pip install

Basic Usage:
``python manage.py patch [subcommand] [user]@[hoststring]``

Examples:
``python manage.py patch woven@192.168.188.10``
``python manage.py patch woven@host.example.com``

For just the current user
``python manage.py patch host.example.com``

You can just patch a part of the deployment with a subcommand.

The possible subcommands are::

    project, templates, static, public, wsgi, webservers

Example:
``python manage.py patch public woven@host.example.com``

activate
--------

Activate a project version

Usage:
``python manage.py activate [version]``

Examples:
``python manage.py activate 0.1``

node
----

Run a no arguments management command on hosts

Basic Usage:
``python manage.py node [command] [user]@[hoststring] --options="[option ...]"``

Examples:
``python manage.py node flush woven@host.example.com --options="--noinput"``




