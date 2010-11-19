Management Commands
===================

Commands that run on a host require a hoststring, role or have HOSTS or ROLEDEFS defined in your settings.

As per fabric a hoststring can be username@hostname, or use just the hostname or ip address. If no username is defined then woven will use the current user or settings.HOST_USER. You never need to set the port. It will always use port 10022 though another port can be defined using the HOST_SSH_PORT setting.

A common and recommended deployment pattern is to separate out staging servers from production servers. To do this in woven you would define your hoststrings in the ROLEDEFS settings (like fabfile roledefs). For example to have one staging server and two production servers you could define::
    
    ROLEDEFS = {'staging':['user@192.168.188.10'], 'production':['user@host1.example.com', user@host2.example.com]}
    
You would then use the role in place of the hoststring e.g. ``python manage.py deploy staging``

setupnode
---------

Setup Ubuntu host[s]. By default this will just setup a baseline host for django deployment but it can be used to setup other types of host such as postgresql nodes and varnish.

By defining ROLEDEFS in your settings you define packages for those hosts in the ROLE_PACKAGES settings. For example to setup a postgresql server you might define a role ROLEDEFS = {'database':['woven@db1.example.com']}, then set ROLE_PACKAGES = {'database':['postgresql']}, and finally set the firewall to ROLE_UFW_RULES = {'database':['allow tcp/5432']}. Finally postgresql configuration can be set in the project TEMPLATES_DIR woven/etc subdirectory.

Basic Usage::

``python manage.py setupnode [hoststring] [options]``

Lets go through what this actually does:

1. Creates the new `user` and disables the `root` user
2. Changes the default ssh port to 10022
3. Uploads your public ssh-key
4. Restricts ssh login to the ssh-key and adds a few other restrictions
5. Adds additional sources `universe` to sources.list
6. Updates and upgrades your packages
7. Installs UFW firewall
8. Installs a baseline of Ubuntu packages including Apache, Nginx, and mod-wsgi
9. Install any etc templates/files sourced from the woven or project woven/etc template directories
10. Sets the timezone according to your settings file


bundle
------

Pip bundle your requirements into pip zip bundles for efficient deployment

``python manage.py bundle``


deploy
------

Deploy your project to host[s] run syncdb and activate

Basic Usage:

``python manage.py deploy [hoststring] [options]``

*options*

The ``--overwrite`` option will remove and re-deploy the entire project.

*South migration options*

deploy integrates with south if it is installed. By default *all* migrations are run.

``-m --migration`` Specify a specific migration to run (see South documentation)

``--fake``  Fake a South migration (see South documentation)

``--nomigration`` Do not migrate

``--manualmigration`` Manage the database migration manually. With this option you can drop out of the current deployment to migrate the database manually, or pause the deployment while migrating in a separate shell. To migrate the database you could login to your host and then run ``workon [yourproject-version]`` to drop into the new versions environment and migrate your database using south, then logout and re-run deploy or continue the existing deploy.

The deploy command does the following:

1. For your first deployment it will deploy your sqlite database
2. Create a virtualenv for the project version
3. Install django. By default it will install the development version. You can set a pip requirements string DJANGO_REQUIREMENT in your settings.py if you want svn trunk or some other specific version
4. Install dependencies from one or more requirement req* files. eg. req, requirements.txt etc. If one doesn't exist then it will create one locally and add woven in it by default.
5. Creates a local sitesettings folder and a settings file for your server [domain].py if it doesn't already exist. You can see how woven lays out your project on the server in the sitesettings file.
6. Deploys your project to the virtualenv on the server
7. Deploys your root (shortest path) TEMPLATE_DIR into a templates directory on the server.
8. Deploys admin media or STATIC_ROOT setting (if you use django-staticfiles) into a virtualenv static directory.
9. Deploys anything at MEDIA_ROOT into a non-virtualenv public directory.
10. Deploys your domain wsgi file into a virtualenv wsgi directory as [domain].wsgi
11. Renders your apache and nginx templates and deploys them into the sites-available with the version in the name.
12. Stops the webservices
13. Syncs the database
14. Runs South migrate if you have South installed
15. Symlinks the webserver conf versions into sites-enabled
16. Symlinks the project virtualenv version to the active virtualenv.
17. Starts the webservices


patch
-----

Patch the current version of your project on host[s] and restart webservices
Includes project, web configuration, media, and wsgi but does not pip install

Basic Usage:

``python manage.py patch [subcommand] [hoststring] [options]``

You can just patch a part of the deployment with a subcommand.

The possible subcommands are::

    project, templates, static, public, wsgi, webconf

Example:

``python manage.py patch public woven@host.example.com``


activate
--------

Activate a project version

Usage:

``python manage.py activate version [options]``

Example:

``python manage.py activate 0.1 woven@host.example.com``

node
----

Run a no arguments management command on host[s]. You can supply command options through the
--options option --options="[option ...]"

Basic Usage:

``python manage.py node command [hoststring] [options]``

Example:

``python manage.py node flush woven@host.example.com --options="--noinput"``

startsites
----------

Create new sitesettings files for new sites, and deploy sitesettings, wsgi, and webconf for the new sites.

Within Django sites are created on the database but use the SITE_ID in the settings file to designate which site is loaded. This command does not create the sites in the database but merely creates and deploys the configuration files needed to serve them.

Basic Usage:

``python manage.py startsites [hoststring] [options]``








