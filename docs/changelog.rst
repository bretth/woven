
Changelog
==========

Release 0.4.0 (10-Aug-2010)
---------------------------------

Note: This release is backwards incompatable with earlier releases. You will need to re-run setupnode and re-deploy your project.

* can now use ROLEDEFS to define roles to group node functionality and use them in commands. ie ./manage.py deploy staging
* moved logs back to /var/log/apache2 nginx etc and link into them instead
* moved almost all woven /etc templates files into a new woven/etc template directory.
* user can create their own woven/etc templates to upload any arbitrary /etc/ files into their corresponding directories on the host
* changed deployment_root to the users home directory to allow integration with virtualenvwrapper
* integrate with virtualenvwrapper. Can now run workon [projectname] to drop into the current version on the node
* added a convenience settings.py, manage.py to sitesettings. The settings.py just imports the first sites settings
* integrate with south for migrations, and added syncdb to activation
* added manage.py patch subcommand where subcommand is an individual part of the deploy process.
* removed unattended upgrades - due to unreliability
* added an modified nginx init.d conf - the default init.d doesn't work under some boot timing circumstances
* use nginx reload command instead of start stop
* symlink the project directory to site-packages

Release 0.3.1 (1-Aug-2010)
--------------------------

* fixed a failure where trying to disable apparmor
* shifted from apache2ctl to init.d for starting and stopping apache2
* fixed an issue with requirements files
* uses the first domain SITE_ID = 1 sitesettings for project settings

Release 0.3 (22-Jul-2010)
-------------------------

* Major api refactor. Moved away from classes to function with decorator pattern. Codebase should be much clearer now.
* abstracted out a generic ``deploy_files`` function into deployment module that uses rsync but is more useful than fabric rsync_project where the remote_dir is not the same as the local parent dir. Stages files for network efficiency, and can deploy specific patterns of files in a directory and render templates if needed.
* new decorator ``run_once_per_host_version`` and state functions simplify where a function may be called multiple times but needs only finish once per host and project version.
* The public api can be imported ``from woven.api import *``
* Allow any host strings to be used instead of just ip addresses.
* Resolves the host string where an ip is needed for apache/nginx
* implements an activate command to activate to a specific project version (env + webserver conf etc)
* ``bundle`` command bundles the requirements files for efficient deployment
* added a template pip requirements file
* added a ``node`` command to run arbitrary django management commands on hosts

Release 0.2.1 (4-Jul-2010)
---------------------------

* Fixed issue with installation fabric dependency

Release 0.2 (3-Jul-2010)
---------------------------

* Added deploy and patch management commands

Release 0.1.1 (22-Jun-2010)
---------------------------

* Changed serverserver to setupnode


Release 0.1 (21-Jun-2010)
-----------------------------

* Initial Release




