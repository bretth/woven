#!/usr/bin/env python
"""
The full public woven api
"""
from fabric.state import env

from woven.decorators import run_once_per_node, run_once_per_version

from woven.deployment import deploy_files, mkdirs
from woven.deployment import upload_template

from woven.environment import check_settings, deployment_root, set_env, patch_project
from woven.environment import get_project_version, server_state, set_server_state
from woven.environment import set_version_state, version_state, get_packages
from woven.environment import post_install_package, post_exec_hook

from woven.project import deploy_static, deploy_media, deploy_project, deploy_db, deploy_templates

from woven.linux import add_user, install_package, port_is_open, skip_disable_root
from woven.linux import install_packages, uninstall_packages
from woven.linux import upgrade_packages, setup_ufw, setup_ufw_rules, disable_root
from woven.linux import add_repositories, restrict_ssh, upload_ssh_key
from woven.linux import change_ssh_port, set_timezone, lsb_release, upload_etc

from woven.virtualenv import activate, active_version
from woven.virtualenv import mkvirtualenv, rmvirtualenv, pip_install_requirements


from woven.webservers import deploy_wsgi, deploy_webconf, start_webserver, stop_webserver, reload_webservers
from woven.webservers import webserver_list

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
    #avoid trying to take shortcuts if setupnode did not finish 
    #on previous execution
    if server_state('setupnode-incomplete'):
        env.overwrite=True
    else: set_server_state('setupnode-incomplete')
    upload_ssh_key()
    restrict_ssh()
    add_repositories()
    upgrade_packages()
    setup_ufw()
    uninstall_packages()
    install_packages()

    upload_etc()
    post_install_package()
    setup_ufw_rules()
    set_timezone()
    set_server_state('setupnode-incomplete',delete=True)
    #stop and start webservers - and reload nginx
    for s in webserver_list():
        stop_webserver(s)
        start_webserver(s)


