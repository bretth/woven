
Changelog
==========

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




