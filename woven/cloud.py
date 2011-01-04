import os, sys

from fabric.state import env
from fabric.api import prompt, settings

from libcloud.types import Provider, NodeState, InvalidCredsException
from libcloud.providers import get_driver

BATCH_SIZE = 10

STATES = {
    0:'RUNNING',
    1:'REBOOTING',
    2:'TERMINATED',
    3:'PENDING',
    4:'UNKNOWN',
}

def connect(provider, secret_key, uid=''):
    """
    Get a cloud connection
    """
    driver = get_driver(eval('Provider.%s'% provider.upper()))
    if uid:
        cloud_conn = driver(uid, secret_key)
    else:
        cloud_conn = driver(secret_key)
    return cloud_conn
    
        
def createnode(named_conf='default', **kwargs):
    """
    Create a node at a provider
    """
    provider = kwargs.pop('provider')
    uid = kwargs.pop('user','')
    if not uid and env.INTERACTIVE:
        uid = prompt('Enter the user/access id for %s (if required):'% provider)
    secret_key = kwargs.pop('key','')
    if not secret_key and env.INTERACTIVE:
        secret_key = prompt('Enter the secret key for %s:'% provider)
    
    conn = connect(provider, secret_key, uid)
    
    kwargs['location'] = get_node_obj(conn, 'location', kwargs.pop('location_id',''))
    kwargs['image'] = get_node_obj(conn, 'image', kwargs.pop('image_id',''))
    kwargs['size'] = get_node_obj(conn, 'size', kwargs.pop('size_id',''))
    
    if 'ec2' in provider:
        keypair = kwargs.get('keypair')
        if not keypair and env.INTERACTIVE:
            keypair = prompt('Enter a name for an ec2 keypair:',default=env.project_name)
        try:
            resp = conn.ex_create_keypair(name = keypair)
        except Exception as inst:
            if not 'InvalidKeyPair.Duplicate' in str(inst):
                raise
            resp = None
            print "Keypair '%s' already exists. Skipping.."% keypair
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
        
    node = conn.create_node(**kwargs)
    
    if env.verbosity:
        # Output some settings for user to copy into settings
        upper_kwargs = {}
        for k in kwargs:
            upper_kwargs[k.upper()] = kwargs[k]

        print "\nNode '%s' created..."% str(node.id)
        if not env.NODES.get(named_conf):
            print "# NODES settings"
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

def destroynode(provider, secret_key, uid, image_id):
    """
    Destroy nodes 
    """
    if not image_id:
        nodes = listnodes(provider, secret_key, uid)
        
    else:
        with settings(verbosity=False):
            nodes = listnodes(provider, secret_key, uid)
        
    resp = False
    conn = connect(provider, secret_key, uid)
    if env.verbosity:
        print "CAUTION: There are no safeguards. A destroyed node may not be recoverable."
    all = False    
    while nodes:
        if not all:
            image_id = prompt('Enter the image # or ALL to destroy node(s), <enter> to exit:')
        if not image_id:
            sys.exit(0)
        elif image_id == 'ALL':
            image_id = 1
            all = True
        try:
            n = nodes.pop(int(image_id)-1)
            resp = conn.destroy_node(n)
            if resp:
                print "Destroyed '%s' on '%s'"% (n.id, provider)
            else:
                print "WARNING: '%s' on '%s' has not confirmed destruction"% (image_id, provider)
                print "Please check directly with the provider"
        except TypeError:
            print "ERROR: Image # must an integer"
        except IndexError:
            if len(nodes) > 1:
                print "ERROR: Image # must be between 1 and", len(nodes)
            else:
                print "ERROR: Invalid Image #"


def get_node_obj(conn, attribute, id):
    """
    Get a Node attribute object
    """
    if env.verbosity:
        print "* Getting %ss"% attribute
    try:
        objs = eval('conn.list_%ss()'% attribute)
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
                print " ID  |  NAME "
            print o.id,'|', o.name
            count += 1

def listhosts(nodes_conf, role=''):
    """
    Get a list of host public ips or hostnames with the given role or default
    from a provider defined by NODES settings
    """
    if role:
        conf = nodes_conf.get(role)
    else:
        conf = nodes_conf.get('default')
    provider = conf.get('PROVIDER')
    uid = conf.get('USER','')
    secret_key = conf.get('KEY')
    if not secret_key:
        print "ERROR: NODES setting for", role, "does not have a KEY"
    
    try:
        conn = connect(provider, secret_key, uid)
        nodes = conn.list_nodes()
    except InvalidCredsException:
        print "ERROR: Invalid NODES settings credentials for", provider
        sys.exit(1)
    except TypeError:
        #libcloud does not handle a missing USER well
        if not uid:
            print "ERROR:", "Cannot list hosts on", provider, ". It may require a NODES USER setting"
            sys.exit(1)
        raise
    # list of hosts that are running
    hosts = [n.public_ip[0] for n in nodes]
else:
    hosts = []
        
    return hosts
        

def listnodes(provider, secret_key, uid):
    """
    List nodes on a provider
    """
    conn = connect(provider, secret_key, uid)
    nodes = conn.list_nodes()
    if env.verbosity:
        print "NODES:"
        print "[ # ] |  ID  | PUBLIC IP or HOST | STATE"
        for (i,n) in  enumerate(nodes):
            print '[', i+1, ']', n.id,'|',n.public_ip[0], '|', STATES.get(n.state,'UNKNOWN')
    return nodes
    