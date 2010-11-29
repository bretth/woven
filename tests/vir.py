from woven.virtualenv import post_deploy

from fabric.state import env

def test_vir_post_deploy():
    env.INSTALLED_APPS = ['example_project.poll']
    post_deploy()
    



