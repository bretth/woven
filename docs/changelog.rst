
Changelog
==========

Release 0.7.0 (8-Dec-2010)
--------------------------

**Changes from 0.6**

* Multi-site functionality has changed dramatically. Instead of using one wsgi file and settings file per domain, woven now uses dynamic SITE_IDs in a single settings file based on the OS user, and process groups in modwsgi. Subdomains with the same SITE_ID can also be catered for by prefixing the settings filename. For example, if the SITE_ID=1 matches example.com, a settings file for the subdomain admin.example.com on the same SITE_ID would be admin_settings.py

* The ubuntu module has become linux. Woven may be compatible with other debian based distributions, and it would be nice to add support for redhat if someone wants to. I don't imagine there is too much difference beyond apt/yum (and ufw) between lsb distros for the purposes of using woven.

* run_once_per_host_version has changed name to run_once_per_version and another decorator has been added run_once_per_node. Both have moved to new decorators module.

**New Features**

* Implemented hooks. Can define a deploy.py with post_setupnode, post_install_package, or post_deploy functions. The deploy.py can be at project level or app level.
* Added a DISABLE_APACHE_MODULES setting to disable a number of unneeded modules on setup.
* Can add Personal Package Archives (PPA's) to a LINUX_PACKAGE_REPOSITORIES setting
* Basic support and template for gunicorn added, and auto adds a PPA for gunicorn
* Backups of configuration files don't pollute the package directories anymore.
* Auto-uninstalls packages that are no longer listed in settings
* Auto-uninstalls or doesn't install Apache modwsgi if you use gunicorn.
* Only uploads templates if they have changed or if any packages are installed
* only installs postgres/mysql db adaptors if your project uses them.

**Bug fixes**

* fix per role/host firewall rules and package installation
* lots of other small improvements..



Release 0.6.1 (26-Nov-2010)
---------------------------

* Fix UFW rules
* Don't try and restart webservers if they don't exist.
* Fixed problem with upload_etc logic
* added very basic templates for postgresql
* don't upload local_settings.py

Release 0.6 (22-Nov-2010)
-------------------------

**Changes from 0.5**

* Bundles are now just .zip files instead of .pybundles. Just rename any existing .pybundles or re-run bundle
* ROOT_DISABLED setting has been named DISABLE_ROOT instead.
* changed the name of the function deploy_public to deploy_media

**New Features**

* added new setting PROJECT_APPS_PATH for local apps, so that you can put an apps folder under your project folder. 
* can now name your distribution differently from your project name
* --overwrite option in deploy to completely remove an existing virtualenv
* handles simple multi database, multi site migrations
* added new setting SSH_KEY_FILENAME which maps to fabric's KEY_FILENAME
* default webconf templates now listen on any ip (not fixed to one)
* can set ufw port rules in a template `woven_project`
* added ENABLE_UFW setting - defaults to true

**Bug fixes**

* fix an issue where you had to name your database after your project
* fix an issue when there is no files in a directory to deploy
* corrected the sitesettings template MEDIA_ROOT and STATIC_ROOT paths 

Release 0.5.3 (9-Nov-2010)
---------------------------

* fix missing dist directory
* fix trailing / in manifest

Release 0.5.2 (7-Nov-2010)
----------------------------

* fix missing import

Release 0.5.1 (25-Aug-2010)
--------------------------------

* fix to setupnode sshd_config rollback
* fix issue where setupnode fails if TEMPLATE_DIRS has not been set.


Release 0.5.0 (16-Aug-2010)
---------------------------------

Note: To upgrade from 0.4 to 0.5 you should move your first [your_project].sitesettings.domain.py to [your_project].sitesettings.settings.py and create a new [your_project].sitesettings.domain.py that just imports [your_project].sitesettings.settings

* changed the [project_name].sitesettings.settings file to be the primary settings file for all non-dev sites
* enable hosts to be setup with different packages through the ROLEDEFS, ROLE_PACKAGES, and ROLE_UFW_RULES settings.
* added a maintenance.html template for nginx
* added a default deny all nginx conf to setupnode
* domains are now determined by dumping sites from the 1st database in the host list being executed against. If the project hasn't deployed we determine from the hostname or ask for it.
* simplified deployment_root and added back in a django setting to override it.
* added --noprofile to env.shell to make peace with virtualenvwrapper
* removed --overwrite option from setupnode
* fixed an issue with syncdb & migrate using the wrong settings file
* changed the name of function deploy_webservers to deploy_webconf
* setupnode now starts/restarts apache2 & nginx at the end of setup


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




