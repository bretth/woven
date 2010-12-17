#!/usr/bin/env python
from optparse import make_option

from fabric.context_managers import settings

from woven.api import deploy
from woven.virtualenv import activate
from woven.management.base import WovenCommand


class Command(WovenCommand):
    """
    Deploy your project to a host and activate
    
    Basic Usage:
    ``python manage.py deploy [user]@[hoststring]``
    
    Examples:
    ``python manage.py deploy woven@192.168.188.10``
    ``python manage.py deploy woven@host.example.com``
    
    For just the current user
    ``python manage.py deploy host.example.com``
    
    """
    option_list = WovenCommand.option_list + (
        make_option('-m', '--migration',
            default='', #use south default run all migrations
            help="Specify a specific migration to run"
        ),
        make_option('--fake',
            action='store_true',
            default=False,
            help="Fake the south migration. Useful when converting an app"
        ),        
        make_option('--nomigration',
            action='store_true',
            default=False,
            help="Do not run any migration"
        ),
        make_option('--manualmigration',
            action='store_true',
            default=False,
            help="Manage the database migration manually"
        ),
        make_option('--overwrite',
            action='store_true',
            default=False,
            help="Overwrite an existing installation"
        ),
        
    )
    help = "Deploy the current version of your project"
    requires_model_validation = False
    
    def handle_host(self,*args, **options):
        self.validate()
        deploy(overwrite=options.get('overwrite'))
        
        with settings(nomigration = options.get('nomigration'),
                      migration = options.get('migration'),
                      manualmigration = options.get('manualmigration')):
            activate()

