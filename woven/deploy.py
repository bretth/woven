from fabric.state import env
from fabric.api import sudo, settings

def post_install_postgresql():
    """
    example default hook for installing postgresql
    """
    from django.conf import settings as s
    with settings(warn_only=True):
        sudo('/etc/init.d/postgresql-8.4 restart')
        sudo("""psql template1 -c "ALTER USER postgres with encrypted password '%s';" """% env.password, user='postgres')
        sudo("psql -f /usr/share/postgresql/8.4/contrib/adminpack.sql", user='postgres')
        if s.DATABASES['default']['ENGINE']=='django.db.backends.postgresql_psycopg2':
            sudo("""psql template1 -c "CREATE ROLE %s LOGIN with encrypted password '%s';" """% (s.DATABASES['default']['USER'],s.DATABASES['default']['PASSWORD']), user='postgres')
            sudo('createdb -T template0 -O %s %s'% (s.DATABASES['default']['USER'],s.DATABASES['default']['NAME']), user='postgres')

        print "* setup postgres user password with your '%s' password"% env.user
        print "* imported the adminpack"
        print "Post install setup of Postgresql complete!"

        
                
    