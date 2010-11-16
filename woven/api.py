#!/usr/bin/env python
"""
The full public woven api
"""
from woven.deployment import deploy_files, mkdirs
from woven.deployment import upload_template, run_once_per_host_version

from woven.environment import check_settings, deployment_root, set_env, patch_project, get_project_version, server_state, set_server_state

from woven.project import deploy_static, deploy_media, deploy_project, deploy_db, deploy_templates

from woven.ubuntu import add_user, apt_get_install, apt_get_purge, port_is_open, skip_disable_root
from woven.ubuntu import install_packages, upgrade_ubuntu, setup_ufw, disable_root
from woven.ubuntu import uncomment_sources, restrict_ssh, upload_ssh_key
from woven.ubuntu import change_ssh_port, set_timezone, ubuntu_version, upload_etc

from woven.virtualenv import activate, active_version
from woven.virtualenv import mkvirtualenv, rmvirtualenv, pip_install_requirements

from woven.webservers import deploy_wsgi, deploy_webconf, start_webservers, stop_webservers, reload_webservers


def deploy(overwrite=False):
    """
    deploy a versioned project on the host
    """
    check_settings()
    if overwrite:
        rmvirtualenv()
    deploy_funcs = [deploy_project,deploy_templates, deploy_static, deploy_media,  deploy_webconf, deploy_wsgi]
    if not patch_project() or overwrite:
        deploy_funcs = [deploy_db,mkvirtualenv,pip_install_requirements] + deploy_funcs
    for func in deploy_funcs: func()


def setupnode(overwrite=False):
    """
    Install a baseline host. Can be run multiple times

    """
    if not port_is_open():
        if not skip_disable_root():
            disable_root()
        port_changed = change_ssh_port()
      
    upload_ssh_key()
    restrict_ssh()
    uncomment_sources()
    upgrade_ubuntu()
    setup_ufw()
    install_packages(overwrite=overwrite)
    upload_etc()
    set_timezone()
    stop_webservers()
    start_webservers()

