Conventions 
============

Woven will use the following conventions to layout your project on the target host.

Apache & Nginx Configuration files
----------------------------------

/etc/apache2/sites-available/
By convention the configuration file will be saved using the domain name as follows.

/etc/apache2/sites-available/example_com-0.1.conf

Nginx is done the sames way


Project Deployment Layout
-------------------------

Root folder for our installation is the domain '~/example.com/'
Within the root folder are the following::

    ~/example.com
        |--database (for sqlite)
        |--dist
            |--requirements-0.1.pybundle (the pybundle if this feature of pip is used)
        |--env (The root directory for all virtual environments)
            |--example_project (symlink to the current virtualenv version)
            |--example_project-0.1 (The virtualenv root for this version)
                |--bin 
                |--include 
                |--lib
                |--project
                    |--example_project (package directory)
                        |--manage.py
                        |--settings.py (for single domain installations only)
                        |--sitesettings (use instead of settings.py for multi-domain installs)
                                |--__init__.py 
                                |--example_com.py (imports default settings and overrides)
                                |--subdomain_example_com.py (imports default settings and overrides)
                |--templates (your project templates go here)
                |--static 
                    |--example.com (for multi-domain deployments, domain specific media can go under the media dir) TO BE IMPLEMENTED
                    |--subdomain.example.com
                |--wsgi (web server scripts go here including wsgi)
    
           |--example_project-0.2 (next release version - as above)
        ...
        |--logs
        |--package_cache (Pip will cache release packages here)
        | Another media directory for files that in the user domain (MEDIA_URL) rather than required for the application
        | These would normally be hosted on something like s3, but you may want to host it locally
        |--public  (for single domain deployments any project media goes here if you are hosting media locally)
            |--example.com (for multi-domain deployments) TO BE IMPLEMENTED
        |--src (pip will store any source repositories here)

Server-side State
---------------------

Woven keeps track of server state and other housekeeping functions using the

`/var/local/woven/` directory

Currently state is stored as a filename with or without content. This may change.




