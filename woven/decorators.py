from functools import wraps

from fabric.api import env
from woven.environment import server_state, set_server_state
from woven.environment import version_state, set_version_state

def run_once_per_node(func):
    """
    Decorator preventing wrapped function from running more than
    once per host (not just interpreter session).

    Using env.patch = True will allow the wrapped function to be run
    if it has been previously executed, but not otherwise
    
    Stores the result of a function as server state
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(env,'patch'): env.patch = False
        state = version_state(func.__name__)
        if not env.patch and state:
            verbose = " ".join([env.host,func.__name__,"completed. Skipping..."])
        elif env.patch and not state:
            verbose = " ".join([env.host,func.__name__,"not previously completed. Skipping..."])
        else:
            results = func(*args, **kwargs)
            verbose =''
            if results: set_version_state(func.__name__,object=results)
            else: set_version_state(func.__name__)
            return results
        if env.verbosity and verbose: print verbose
        return             
          
    return decorated

def run_once_per_version(func):
    """
    Decorator preventing wrapped function from running more than
    once per host and env.project_fullname (not just interpreter session).

    Using env.patch = True will allow the function to be run
    
    Stores the result of a function as server state
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        if not hasattr(env,'patch'): env.patch = False
        state = version_state(func.__name__)
        if not env.patch and state:
            verbose = " ".join([env.host,func.__name__,"completed. Skipping..."])
        elif env.patch and not state:
            verbose = " ".join([env.host,func.__name__,"not previously completed. Skipping..."])
        else:
            results = func(*args, **kwargs)
            verbose =''
            if results: set_version_state(func.__name__,object=results)
            else: set_version_state(func.__name__)
            return results
        if env.verbosity and verbose: print verbose
        return             
          
    return decorated