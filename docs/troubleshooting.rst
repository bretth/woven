Troubleshooting
===============

Stuff happens.

**setupnode hangs on upgrade**

Most likely some package in the apt-get upgrade process is incorrectly asking for user input.

*do not kill the process at the client end*

This will most likely leave your Ubuntu package database in a broken state.

The best solution is to log directly onto the host without killing the hung setupnode and then run sudo apt-get upgrade directly on the host. It will need you to dpkg configure -a and possibly remove the /var/lib/dpkg/updates if you are still having issues.

**ERROR: There was an error running ./manage.py on the node**

By deploying early and often it will be easier to diagnose misconfiguration issues.
Usually this error will mean that django can't initialize your project due to import or other related issues, due to a particular app or code within your project.
In the event it is a particular version of one of your requirements you can overwrite an existing installation by running ``./manage.py deploy --overwrite`` which will wipe your existing failed deployment.




