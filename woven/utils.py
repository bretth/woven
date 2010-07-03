#!/usr/bin/env python
from __future__ import with_statement

import os, shutil, sys, tempfile
from functools import wraps
from pkg_resources import parse_version

from django.template.loader import render_to_string

from fabric.api import env,  local, put, run, sudo, prompt
from fabric.contrib.files import append, exists, contains
from fabric.context_managers import cd, hide, settings

from woven.global_settings import woven_env

def active_version():
    """
    Determine the current active version on the server
    
    Just examine the which environment is symlinked
    """
    link = env.deployment_root+'/'.join(['env',env.project_name])

    if not exists(link): return None
    active = run('ls -al '+link).split(' -> ')[1]
    if active[-1] == '/': active = active[:-1]

    return active.split('/')[-1]

def backup_file(path):
    """
    Backup a file but never overwrite an existing backup file
    """
    if not exists(path+'.wovenbak'):
        sudo('cp '+path+' '+path+'.wovenbak')

def restore_file(path, delete_backup=True):
    """
    Restore a file if it exists and remove the backup
    """
    if exists(path+'.wovenbak'):
        if delete_backup:
            sudo('mv -f '+path+'.wovenbak '+path)
        else:
            sudo('cp -f '+path+'.wovenbak '+path)
   
def set_server_state(name,content='',delete=False):
    """
    Sets a simple 'state' on the server by creating a file
    with the desired state's name and echoing content if supplied
    """
    with settings(warn_only=True):
        #Test for os state
        if not exists('/var/local/woven', use_sudo=True):
            sudo('mkdir /var/local/woven')
    if not delete:
        sudo('touch /var/local/woven/%s'% name)
        if content:
            sudo("echo '%s' > /var/local/woven/%s"% (content,name))
    else:
        sudo('rm -f /var/local/woven/%s'% name)

def server_state(name, prefix=False):
    """
    If the server state exists return the file as a string or True if
    no content exists.
    
    If prefix returns True if any files exist with ls name*
    """
    
    if not prefix and exists('/var/local/woven/%s'% name, use_sudo=True):
        content = sudo('cat /var/local/woven/%s'% name).strip()
        if content:
            return content
        else:
            return True
    elif prefix:
        with settings(warn_only=True):
            state = sudo('ls /var/local/woven/%s*'% name)
        if state.failed:
            return False
        else:
            return True
        
    else:
        return False

def interactive():
    if not hasattr(env, 'INTERACTIVE'):
        env.INTERACTIVE = False
    return env.INTERACTIVE

def project_version(version=''):
    if not env.project_version or version:
        env.project_version = parse_project_version(version)
    return env.project_version
    

def project_name():
    """
    Get the project name from the setup.py
    """
    if not hasattr(env,'project_name'):
        env.project_name = local('python setup.py --name').rstrip()
    return env.project_name

def project_fullname(version=''):
    env.project_fullname = project_name() + '-' + project_version(version)
    return env.project_fullname
        
def parse_project_version(version=''):
    """
    Returns the significant part of the version excluding the build
       
    The final forms returned can be
    
    major.minor
    major.minor stage (spaces will be replaced with '-')
    major.minor.stage
    major.minor-stage
    major.minorstage (eg 1.0rc1)
    major.minor.maintenance
    major.minor.maintenance-stage
    major.minor.maintenancestage
    
    Anything beyond the maintenance or stage whichever is last is ignored 
    
    """
    
    def mm_version(vers):
        stage = ''
        stage_sep = ''
        finalvers = ''
        if not vers.isdigit():
            for num,char in enumerate(vers):
                if char.isdigit():
                    finalvers += str(char)
                elif char.isalpha():
                    stage = vers[num:]
                    break
                elif char in [' ','-']: #sep
                    #We will strip spaces to avoid needing to 'quote' paths
                    stage_sep = '-'
                    stage = vers[num+1:]
                    break
        else:
            finalvers = vers
        #remove any final build numbers
        if ' ' in stage:
            stage = stage.split(' ')[0]
        elif '-' in stage:
            stage = stage.split('-')[0]
        return (finalvers,stage,stage_sep)
        
    if not version:
        version = local('python setup.py --version').rstrip()
    v = version.split('.')
    major = v[0]
    minor = v[1]
    maint = ''
    stage = ''
    if len(v)>2 and v[2]<>'0': #(1.0.0 == 1.0)
        maint = v[2]
    if len(v)>3 and v[3][0].isalpha():
        stage = v[3]
        project_version = '.'.join([major,minor,maint,stage])
    else:
        #Detect stage in minor
        minor,stage_minor,stage_minor_sep = mm_version(minor)
        if maint: #may be maint = ''
            maint, stage_maint, stage_maint_sep = mm_version(maint)
        else:
            stage_maint = ''; stage_maint_sep = ''
        if stage_minor:
            stage = stage_minor
            stage_sep = stage_minor_sep
        elif stage_maint:
            stage = stage_maint
            stage_sep = stage_maint_sep
        finalvers = [major,minor]
        if maint: finalvers.append(maint)
        finalvers = '.'.join(finalvers)
        if stage:
            finalvers = stage_sep.join([finalvers,stage])
        project_version = finalvers
   
    return project_version

def rmtmpdirs():
    for path in env.woventempdirs:
        shutil.rmtree(path,ignore_errors=True)

def root_domain():
    """
    Deduce the root domain name, usually a 'naked' domain but not necessarily. 
    """
    if not hasattr(env,'root_domain'):
        cwd = os.getcwd().split(os.sep)
        domain = ''
        #we'll just pick the first directory in the path which has a period.
        for d in cwd:
            if '.' in d: 
                domain = d
        if not domain and interactive():
            domain = prompt('Enter the root domain for this project ie example.com',default='example.com')
        else:
            domain = 'example.com'
        env.root_domain = domain
    return env.root_domain
  
def upload_template(filename,  destination,  context={},  use_sudo=False):
    """
    Render and upload a template text file to a remote host using the Django
    template api. 

    ``filename`` should be the Django template name.
    
    ``context`` is the Django template dictionary context to use.

    The resulting rendered file will be uploaded to the remote file path
    ``destination`` (which should include the desired remote filename.) If the
    destination file already exists, it will be renamed with a ``.bak``
    extension.

    By default, the file will be copied to ``destination`` as the logged-in
    user; specify ``use_sudo=True`` to use `sudo` instead.
    """
    #Replaces the default fabric.contrib.files.upload_template
    basename = os.path.basename(filename)
    text = render_to_string(filename,context)
    temp_destination = '/tmp/' + basename

    # This temporary file should not be automatically deleted on close, as we
    # need it there to upload it (Windows locks the file for reading while open).
    tempfile_fd, tempfile_name = tempfile.mkstemp()
    output = open(tempfile_name, "w+b")

    output.write(text)
    output.close()

    # Upload the file.
    put(tempfile_name, temp_destination)
    os.close(tempfile_fd)
    os.remove(tempfile_name)

    func = use_sudo and sudo or run
    # Back up any original file (need to do figure out ultimate destination)
    to_backup = destination
    with settings(hide('everything'), warn_only=True):
        # Is destination a directory?
        if func('test -f %s' % to_backup).failed:
            # If so, tack on the filename to get "real" destination
            to_backup = destination + '/' + basename
    if exists(to_backup):
        backup_file(to_backup)
    # Actually move uploaded template to destination
    func("mv %s %s" % (temp_destination, destination))

    