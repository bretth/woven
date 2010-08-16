
Woven is a Python library built on `Fabric <http://docs.fabfile.org/0.9.1/>`_ which aims to deploy versioned Django
projects served by Apache and Nginx on Ubuntu Linux servers. 

Woven grew out of a simple fabric script that followed Will Larson's
`Ubuntu intrepid almanac <http://lethain.com/entry/2009/feb/13/the-django-and-ubuntu-intrepid-almanac/>`_. Out of the box there is a fair bit of tedious work in setting up a server environment for Django. Modern Django projects can also be a cosmopolitan mix of source repositories and binary packages which makes keeping a development environment in sync with production challenging. Where traditional rsync and source repository scripts fall far short, Woven utilizes Pip, Virtualenv, Fabric and Django templates to simplify deployment making *release early and often* a reality.

Woven provides four core Django commands/functions; ``setupnode``, ``deploy``, ``patch``, ``activate`` and a standard webserver configuration that you can change as required. Additionally Woven can be integrated into standard Fabric fabfile.py scripts as projects grow in complexity.

.. note::

    Woven is still alpha software, and the api and conventions may change between versions. It is not recommended for production deployment at this stage. It has been tested (in the most loose sense of the term) on OSX using Ubuntu Server 10.04 hosts, but should work with 9.10. It currently won't work with Windows, due to use of rsync.
    
    