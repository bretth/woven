#!/usr/bin/env python

from django.core import management
from django.utils import importlib
import sys, os

if __name__ == "__main__":
    #Inject woven into the settings only if it is a woven command
    settings_mod = None; inject = False
    for arg in sys.argv:
        if '--settings' in arg:
            settings_mod = arg.split('=')[1].strip()
        elif arg in ['activate','deploy','startsites','setupnode','node','bundle','patch']:
            inject = True
    if inject:
        if settings_mod:
            os.environ['DJANGO_SETTINGS_MODULE'] = settings_mod
        try:
            from django.conf import settings
            settings.INSTALLED_APPS += ('woven',)
            
            #switch to the settings module directory
            proj = settings_mod.split('.')[0]
            proj_mod = importlib.import_module(proj)
            moddir = os.path.dirname(proj_mod.__file__)
            os.chdir(moddir)
        except ImportError:
            pass
    #run command as per django-admin.py
    management.execute_from_command_line()

