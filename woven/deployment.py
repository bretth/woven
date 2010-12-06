#!/usr/bin/env python
from functools import wraps
from glob import glob
from hashlib import sha1
import os, shutil, sys, tempfile

from django.template.loader import render_to_string

from fabric.state import env
from fabric.operations import run, sudo, put
from fabric.context_managers import cd, settings, hide
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project

def _backup_file(path):
    """
    Backup a file but never overwrite an existing backup file
    """
    backup_base = '/var/local/woven-backup'
    backup_path = ''.join([backup_base,path])
    if not exists(backup_path):
        directory = ''.join([backup_base,os.path.split(path)[0]])
        sudo('mkdir -p %s'% directory)
        sudo('cp %s %s'% (path,backup_path))

def _restore_file(path, delete_backup=True):
    """
    Restore a file if it exists and remove the backup
    """
    backup_base = '/var/local/woven-backup'
    backup_path = ''.join([backup_base,path])
    if exists(backup_path):
        if delete_backup:
            sudo('mv -f %s %s'% (backup_path,path))
        else:
            sudo('cp -f %s %s'% (backup_path,path))


def _get_local_files(local_dir, pattern=''):
    """
    Returns a dictionary with directories as keys, and filenames as values
    for filenames matching the glob ``pattern`` under the ``local_dir``
    ``pattern can contain the Boolean OR | to evaluated multiple patterns into
    a combined set. 
    """
    local_files = {}
    
    if pattern:
        cwd = os.getcwd()
        os.chdir(local_dir)
        patterns = pattern.split('|')
        local_list = set([])
        for p in patterns: local_list = local_list | set(glob(p))
        for path in local_list:
            dir, file = os.path.split(path)
            if os.path.isfile(path):
                local_files[dir] = local_files.get(dir,[])+[file]
            elif os.path.isdir(path):
                local_files[file] = local_files.get(dir,[])
        os.chdir(cwd)
    return local_files

def _stage_local_files(local_dir, local_files={}):
    """
    Either ``local_files`` and/or ``context`` should be supplied.
    
    Will stage a ``local_files`` dictionary of path:filename pairs where path
    is relative to ``local_dir`` into a local tmp staging directory.
    
    Returns a path to the temporary local staging directory

    """
    staging_dir = os.path.join(tempfile.mkdtemp(),os.path.basename(local_dir))
    os.mkdir(staging_dir)
    for root, dirs, files in os.walk(local_dir):
        relative_tree = root.replace(local_dir,'')
        if relative_tree:
            relative_tree = relative_tree[1:]
        if local_files:
            files = local_files.get(relative_tree,[])
        for file in files:
            if relative_tree:
                filepath = os.path.join(relative_tree,file)
                if not os.path.exists(os.path.join(staging_dir,relative_tree)):
                    os.mkdir(os.path.join(staging_dir,relative_tree))
            else: filepath = file
            shutil.copy2(os.path.join(root,file),os.path.join(staging_dir,filepath))
    return staging_dir

def deploy_files(local_dir, remote_dir, pattern = '',rsync_exclude=['*.pyc','.*'], use_sudo=False):
    """
    Generic deploy function for cases where one or more files are being deployed to a host.
    Wraps around ``rsync_project`` and stages files locally and/or remotely
    for network efficiency.
    
    ``local_dir`` is the directory that will be deployed.
   
    ``remote_dir`` is the directory the files will be deployed to.
    Directories will be created if necessary.
    
    Note: Unlike other ways of deploying files, all files under local_dir will be
    deployed into remote_dir. This is the equivalent to cp -R local_dir/* remote_dir.

    ``pattern`` finds all the pathnames matching a specified glob pattern relative
    to the local_dir according to the rules used by the Unix shell.
    ``pattern`` enhances the basic functionality by allowing the python | to include
    multiple patterns. eg '*.txt|Django*'
     
    ``rsync_exclude`` as per ``rsync_project``
    
    Returns a list of directories and files created on the host.
    
    """
    #normalise paths
    if local_dir[-1] == os.sep: local_dir = local_dir[:-1]
    if remote_dir[-1] == '/': remote_dir = remote_dir[:-1]
    created_list = []
    staging_dir = local_dir
    
    #resolve pattern into a dir:filename dict
    local_files = _get_local_files(local_dir,pattern)
    #If we are only copying specific files or rendering templates we need to stage locally
    if local_files: staging_dir = _stage_local_files(local_dir, local_files)
    remote_staging_dir = '/home/%s/.staging'% env.user
    if not exists(remote_staging_dir):
        run(' '.join(['mkdir -pv',remote_staging_dir])).split('\n')
        created_list = [remote_staging_dir]
    
    #upload into remote staging
    rsync_project(local_dir=staging_dir,remote_dir=remote_staging_dir,exclude=rsync_exclude,delete=True)

    #create the final destination
    created_dir_list = mkdirs(remote_dir, use_sudo)
    
    if not os.listdir(staging_dir): return created_list

    func = use_sudo and sudo or run
    #cp recursively -R from the staging to the destination and keep a list
    remote_base_path = '/'.join([remote_staging_dir,os.path.basename(local_dir),'*'])
    copy_file_list = func(' '.join(['cp -Ruv',remote_base_path,remote_dir])).split('\n')
    if copy_file_list[0]: created_list += [file.split(' ')[2][1:-1] for file in copy_file_list if file]

    #cleanup any tmp staging dir
    if staging_dir <> local_dir:
        shutil.rmtree(staging_dir,ignore_errors=True)
    
    return created_list

def mkdirs(remote_dir, use_sudo=False):
    """
    Wrapper around mkdir -pv
    
    Returns a list of directories created
    """
    func = use_sudo and sudo or run
    result = func(' '.join(['mkdir -pv',remote_dir])).split('\n')
    #extract dir list from ["mkdir: created directory `example.com/some/dir'"]
    if result[0]: result = [dir.split(' ')[3][1:-1] for dir in result if dir]
    return result

def upload_template(filename,  destination,  context={},  use_sudo=False, backup=True, modified_only=False):
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

    func = use_sudo and sudo or run
    
    #check hashed template on server first
    if modified_only:
        hashfile_dir, hashfile = os.path.split(destination)
        hashfile_dir = ''.join(['/var/local/woven-backup',hashfile_dir])
        hashfile = '%s.hashfile'% hashfile
        hashfile_path = os.path.join(hashfile_dir, hashfile)
        hashed = sha1(text).hexdigest()
        if hashfile:
            if not exists(hashfile_dir): sudo('mkdir -p %s'% hashfile_dir)
            sudo('touch %s'% hashfile_path) #store the hash near the template
            previous_hashed = sudo('cat %s'% hashfile_path).strip()
            if previous_hashed == hashed:
                return False
            else: sudo('echo %s > %s'% (hashed, hashfile_path))

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

    
    # Back up any original file (need to do figure out ultimate destination)
    if backup:
        to_backup = destination
        with settings(hide('everything'), warn_only=True):
            # Is destination a directory?
            if func('test -f %s' % to_backup).failed:
                # If so, tack on the filename to get "real" destination
                to_backup = destination + '/' + basename
        if exists(to_backup):
            _backup_file(to_backup)
    # Actually move uploaded template to destination
    func("mv %s %s" % (temp_destination, destination))
    return True