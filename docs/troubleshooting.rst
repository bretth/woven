Troubleshooting
===============

Stuff happens.

**setupnode hangs on upgrade (10.04)**

Most likely some part of the apt-get upgrade process is incorrectly asking for user input. The best solution is to log directly onto the server without killing the hung setupnod and then run sudo apt-get upgrade directly on the server. It will need you to dpkg configure -a and possibly remove the /var/lib/dpkg/updates if you are still having issues. 



