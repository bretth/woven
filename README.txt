
Woven is a Python library built on `Fabric <http://docs.fabfile.org/>`_ which aims to deploy versioned Django projects served by Apache and Nginx on Ubuntu Linux servers.

**Features:**

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
    
.. note::

    Woven is still alpha software, and the api and conventions may change between versions. It is not recommended for production deployment at this stage. It has been tested (in the most loose sense of the term) on OSX using Ubuntu Server 10.04 hosts and greater, but should work with 9.10. It currently *won't* work with Windows, due to use of rsync.

