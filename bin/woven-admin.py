#!/usr/bin/env python
import sys, os
from distutils.core import run_setup
from random import choice
import re
import optparse

from django.core.management import execute_from_command_line, call_command
from django.core.management.base import CommandError, _make_writeable
from django.utils.importlib import import_module

from fabric.contrib.console import confirm, prompt
from fabric.api import settings
from fabric.state import env
from fabric.main import find_fabfile

import woven

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.realpath(woven.__file__))
                                ,'templates','distribution_template')

def copy_helper(app_or_project, name, directory, dist, template_dir, noadmin):
    """
    
    Replacement for django copy_helper
    Copies a Django project layout template into the specified distribution directory

    """

    import shutil
    if not re.search(r'^[_a-zA-Z]\w*$', name): # If it's not a valid directory name.
        # Provide a smart error message, depending on the error.
        if not re.search(r'^[_a-zA-Z]', name):
            message = 'make sure the name begins with a letter or underscore'
        else:
            message = 'use only numbers, letters and underscores'
        raise CommandError("%r is not a valid project name. Please %s." % (name, message))
    top_dir = os.path.join(directory, dist)
    try:
        os.mkdir(top_dir)
    except OSError, e:
        raise CommandError(e)
        
    for d, subdirs, files in os.walk(template_dir):
        relative_dir = d[len(template_dir)+1:].replace('project_name', name)
        if relative_dir:
            os.mkdir(os.path.join(top_dir, relative_dir))
        for subdir in subdirs[:]:
            if subdir.startswith('.'):
                subdirs.remove(subdir)
        for f in files:
            if not f.endswith('.py'):
                # Ignore .pyc, .pyo, .py.class etc, as they cause various
                # breakages.
                continue
            path_old = os.path.join(d, f)
            path_new = os.path.join(top_dir, relative_dir, f.replace('project_name', name))
            fp_old = open(path_old, 'r')
            fp_new = open(path_new, 'w')
            if noadmin:
                fp_new.write(fp_old.read().replace('{{ project_name }}', name))
            else:
                fp_new.write(fp_old.read().replace('{{ project_name }}', name).replace('## ',''))
            fp_old.close()
            fp_new.close()
            try:
                shutil.copymode(path_old, path_new)
                _make_writeable(path_new)
            except OSError:
                sys.stderr.write(style.NOTICE("Notice: Couldn't set permission bits on %s. You're probably using an uncommon filesystem setup. No problem.\n" % path_new))


def start_distribution(project_name, template_dir, dist, noadmin):
    """
    Custom startproject command to override django default
    """

    directory = os.getcwd()

    # Check that the project_name cannot be imported.
    try:
        import_module(project_name)
    except ImportError:
        pass
    else:
        raise CommandError("%r conflicts with the name of an existing Python module and cannot be used as a project name. Please try another name." % project_name)
    #woven override
    copy_helper('project', project_name, directory, dist, template_dir, noadmin)
    
    #Create a random SECRET_KEY hash, and put it in the main settings.
    main_settings_file = os.path.join(directory, dist, project_name, 'settings.py')
    settings_contents = open(main_settings_file, 'r').read()
    fp = open(main_settings_file, 'w')
    secret_key = ''.join([choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(50)])
    settings_contents = re.sub(r"(?<=SECRET_KEY = ')'", secret_key + "'", settings_contents)
    fp.write(settings_contents)
    fp.close()
    
    #import settings and create start directories
    sys.path.append(os.path.join(directory, dist))

    s = import_module('.'.join([project_name,'settings']))
    sys.path.pop()
    if s.DATABASES['default']['ENGINE']=='django.db.backends.sqlite3':
        if s.DATABASES['default']['NAME'] and not os.path.exists(s.DATABASES['default']['NAME']):
            os.mkdir(os.path.dirname(s.DATABASES['default']['NAME']))
    if s.STATIC_ROOT and os.path.isabs(s.STATIC_ROOT) and not os.path.exists(s.STATIC_ROOT):
        os.mkdir(s.STATIC_ROOT)
    if s.MEDIA_ROOT and os.path.isabs(s.MEDIA_ROOT) and not os.path.exists(s.MEDIA_ROOT):
        os.mkdir(s.MEDIA_ROOT)
    if s.TEMPLATE_DIRS:
        for t in s.TEMPLATE_DIRS:
            if not os.path.exists(t) and os.path.sep in t:
                os.mkdir(t)
    

if __name__ == "__main__":
    #Inject woven into the settings only if it is a woven command
    settings_mod = None
    inject = False
    startproject = False
    orig_cwd = os.getcwd()

    for arg in sys.argv:
        if '--settings' in arg:
            settings_mod = arg.split('=')[1].strip()
        elif arg in ['activate','deploy','startsites','setupnode','node','bundle','patch', 'validate']:
            inject = True
        elif arg == 'startproject':
            #call woven startproject in place of django startproject
            startproject = True
            inject = True
            parser = optparse.OptionParser(usage="usage: %prog startproject [project_name] [username@domain] [options]\n\n"
                "project_name is the name of your django project\n"                               
                "username@domain is an optional email address to setup a superuser")
            parser.add_option('-t', '--template-dir', dest='src_dir',
                        help='project template directory to use',
                        default=TEMPLATE_DIR)
            parser.add_option('-d','--dist', dest='dist_name',
                        help="alternative distribution name",
                        default='')
            parser.add_option('--noadmin',
                    action='store_true',
                    default=False,
                    help="admin disabled",
                    ),
            parser.add_option('--nosyncdb',
                    action='store_true',
                    default=False,
                    help="Does not syncdb",
                    )
            options, args = parser.parse_args()
            if len(args) not in (2, 3, 4):
                parser.print_help()
                sys.exit(1)
            if not options.dist_name:
                dist = args[1]
            else:
                dist = options.dist_name
            project_name = args[1]
            try:
                email = args[2]
            except IndexError:
                email = ''

            start_distribution(project_name,options.src_dir, dist, noadmin = options.noadmin)

    #get the name of the settings from setup.py if DJANGO_SETTINGS_MODULE is not set
    if not os.environ.get('DJANGO_SETTINGS_MODULE') and not settings_mod:
        if startproject:
            os.chdir(os.path.join(orig_cwd,dist))
        elif not 'setup.py' in os.listdir(os.getcwd()):
            #switch the working directory to the distribution root where setup.py is
            with settings(fabfile='setup.py'):
                env.setup_path = find_fabfile()
            if not env.setup_path:
                print 'Error: You must have a setup.py file in the current or a parent folder'
                sys.exit(1)
            local_working_dir = os.path.split(env.setup_path)[0]
            os.chdir(local_working_dir)
        
        woven_admin = sys.argv[0]
        setup = run_setup('setup.py',stop_after="init")
        settings_mod = '.'.join([setup.packages[0],'settings'])
        os.environ['DJANGO_SETTINGS_MODULE'] =  settings_mod
        sys.argv.remove('setup.py')
        sys.argv.insert(0, woven_admin)


    if inject:
        if settings_mod:
            os.environ['DJANGO_SETTINGS_MODULE'] = settings_mod

        from django.conf import settings
        settings.INSTALLED_APPS += ('woven',)
        
        #switch to the settings module directory
        proj = settings_mod.split('.')[0]
        proj_mod = import_module(proj)
        if not proj_mod:
            sys.exit(0)
        moddir = os.path.dirname(proj_mod.__file__)
        os.chdir(moddir)

    
    if startproject:
        if not options.nosyncdb:
            call_command('syncdb',interactive=False)
            if 'django.contrib.auth' in settings.INSTALLED_APPS:
                if '@' in email:
                    u = email.split('@')[0]
                else:
                    u = project_name
                    email = '%s@example.com'% project_name
                print "\nA superuser will be created with '%s' as username and password"% u
                print "Alternatively you can run the standard createsuperuser command separately"
                csuper = confirm('Would you like to create a superuser now?',default=True)
                if csuper:
                    from django.contrib.auth.models import User
                    
                    User.objects.create_superuser(username=u, email=email, password=u)
                    print "\nA default superuser was created:"
                    print "Username:", u
                    print "Password:", u
                    print "Email:", email
                    print "Change your password with 'woven-admin.py changepassword %s'"% u
                else:
                    print "\nNo superuser created. "
                    print "Run 'woven-admin.py createsuperuser' to create one"
        
    #run command as per django-admin.py
    else:
        #switch back to the original directory just in case some command needs it
        os.chdir(orig_cwd)
        execute_from_command_line()

