
Woven is a Python library built on `Fabric <http://docs.fabfile.org/0.9.1/>`_ which aims to deploy versioned Django
projects served by Apache and Nginx on Ubuntu Linux servers.

Woven grew out of a simple fabric script that replicated Will Larson's
`Ubuntu intrepid almanac <http://lethain.com/entry/2009/feb/13/the-django-and-ubuntu-intrepid-almanac/>`_.

At the current version Woven does just one simple thing which Django developers
may find useful - provide a management command ``setupserver`` to
setup one or more baseline Ubuntu servers for deploying a Django project.

.. note::

    Woven is still alpha software and will no doubt destroy your production system.
    It has been tested (in the most loose sense of the term) on OSX using Ubuntu Server 10.04 hosts,
    but should work with 9.10. I don't think it will work with Windows, though patches are welcome.
    
    