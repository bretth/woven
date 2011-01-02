import os, sys

from fabric.state import env
from fabric.api import prompt

from libcloud.types import Provider
from libcloud.providers import get_driver

BATCH_SIZE = 15
cloud_conn = None

def createnode(named_conf='default', **kwargs):
    """
    Create a node at a provider
    """
    provider = kwargs.pop('provider')
    Driver = get_driver(eval('Provider.%s'% provider.upper()))
    uid = kwargs.pop('user','')
    if not uid and env.INTERACTIVE:
        uid = prompt('Enter the user/access id for %s (if required):'% provider)
    secret_key = kwargs.pop('key','')
    if not secret_key and env.INTERACTIVE:
        secret_key = prompt('Enter the secret key for %s:'% provider)
    
    global cloud_conn   
    if uid:
        cloud_conn = Driver(uid, secret_key)
    else:
        cloud_conn = Driver(secret_key)

    kwargs['location'] = get_node_obj('location', kwargs.pop('location_id',''))
    kwargs['image'] = get_node_obj('image', kwargs.pop('image_id',''))
    kwargs['size'] = get_node_obj('size', kwargs.pop('size_id',''))

    
    if 'ec2' in provider:
        keypair = kwargs.get('keypair')
        if not keypair and env.INTERACTIVE:
            keypair = prompt('Enter a name for an ec2 keypair:',default=env.project_name)
        try:
            resp = cloud_conn.ex_create_keypair(name = keypair)
        except Exception as inst:
            if not 'InvalidKeyPair.Duplicate' in str(inst):
                raise
            resp = None
            print "WARNING: Duplicate keypair '%s'. Skipping.."% keypair
        if resp:
            keymaterial = resp.get('keyMaterial')
            keyfile = '%s.pem'% env.project_name
            f = open(keyfile, "w")
            f.write(keymaterial+'\n')
            f.close()
            os.chmod(keyfile,0600)
            if env.verbosity:
                print "Created ssh key file", os.path.abspath(keyfile)
                
        kwargs['ex_keyname'] = keypair
        
    node = cloud_conn.create_node(**kwargs)
    
    if env.verbosity:
        # Output some settings for user to copy into settings
        upper_kwargs = {}
        for k in kwargs:
            upper_kwargs[k.upper()] = kwargs[k]

        print "\nNode '%s' created with the settings:"% str(node.id)
        print "NODES = {"
        print "    '%s': {"% named_conf
        print "        'PROVIDER': '%s',"% provider
        print "        'USER': '%s',"% uid
        print "        'KEY': '%s',"% secret_key
        print "        'LOCATION_ID': '%s',"% upper_kwargs.pop('LOCATION').id
        print "        'IMAGE_ID': '%s',"% upper_kwargs.pop('IMAGE').id
        print "        'SIZE_ID': '%s',"% upper_kwargs.pop('SIZE').id
        keys = upper_kwargs.keys()
        keys.sort()
        for k in keys:
            print "        '%s': '%s',"% (k,upper_kwargs.pop(k))
        print "        }"
        print "}"

def get_node_obj(attribute, id):
    """
    Get a Node attribute object
    """
    if env.verbosity:
        print "* Getting %ss"% attribute
    try:
        objs = eval('cloud_conn.list_%ss()'% attribute)
        obj_ids = [o.id for o in objs]
    except NotImplementedError:
        return
    if len(obj_ids) == 1:
        return objs[0]
    while True:
        if not id:
            id = prompt('Enter the %s id to use or <enter> to list:'% attribute)
        count = 1 
        for o in objs:
            if count == BATCH_SIZE:
                id = prompt('Enter a %s id or <enter> for more:'% attribute)
                count = 0
            if id:
                try:
                    o = objs[obj_ids.index(id)]
                    return o
                except ValueError:
                    print "ERROR: %s is not a valid %s id"% (id, attribute)
                    id = ''
            if not count:
                print "%s:"% attribute.upper()
                print "id | name"
            count += 1

            print o.id,'|', o.name    
