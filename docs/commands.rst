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

Deploy your project to a host and activate

Basic Usage:
``python manage.py deploy [user]@[hoststring]``

Examples:
``python manage.py deploy woven@192.168.188.10``
``python manage.py deploy woven@host.example.com``

For just the current user
``python manage.py deploy host.example.com``

patch
-----

Patch the current version of your project on hosts and restart webservices
Includes project, web configuration, media, and wsgi but does not pip install

Basic Usage:
``python manage.py patch [user]@[hoststring]``

Examples:
``python manage.py patch woven@192.168.188.10``
``python manage.py patch woven@host.example.com``

For just the current user
``python manage.py patch host.example.com``

activate
--------

Activate a project version

Usage:
``python manage.py activate [version]

Examples:
``python manage.py activate 0.1``

node
----

Run a no arguments management command on a host

Basic Usage:
``python manage.py node [command] [user]@[hoststring] --options="[option ...]"``

Examples:
``python manage.py node flush woven@host.example.com --options="--noinput"``




