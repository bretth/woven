
Woven is a Python library built on `Fabric <http://docs.fabfile.org/0.9.1/>`_ which aims to deploy versioned Django
projects served by Apache and Nginx on Ubuntu Linux servers.

Woven grew out of a simple fabric script that replicated Will Larson's
`Ubuntu intrepid almanac <http://lethain.com/entry/2009/feb/13/the-django-and-ubuntu-intrepid-almanac/>`_. With the price of virtual servers declining, having your own private vm is much more feasible even for small projects, but out of the box there is a fair bit of tedious work in setting up a server environment for Django.

Woven currently provides three core Django commands/functions; ``setupnode``, ``deploy``, ``patch`` and a standard webserver configuration that aims for stability and flexibility. Additionally Woven can be integrated into standard fabfile.py scripts as projects grow in complexity.

.. note::

    Woven is still alpha software and will no doubt destroy your production system. 
    It has been tested (in the most loose sense of the term) on OSX using Ubuntu Server 10.04 hosts,
    but should work with 9.10. It currently won't work with Windows, due to use of rsync.
    
    