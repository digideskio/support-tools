#!/usr/bin/env python

import os
import time

from fabric.api import task, env, run, sudo, execute
from fabric.contrib import files

env.use_ssh_config = True
env.forward_agent = True

datetime_format = '%Y%m%d%H%M%S'
env.hosts    = ['support-tools-1.vpc3.10gen.cc']

app          = 'support-tools'
repo         = 'git@github.com:10gen/support-tools'
env.environment  = 'prod'
group        = 'support-tools'

piddir = '/var/run/10gen'
logdir = '/var/log/10gen'

@task
def vagrant():
    # fab vagrant deploy
    env.environment  = 'dev'
    set_variables()

    env.user = 'vagrant'
    env.hosts = ['127.0.0.1:2222']
    env.key_filename = '~/.vagrant.d/insecure_private_key'

    execute(vagrant_group)

def vagrant_group():
    sudo('usermod -a -G {0} vagrant'.format(env.deploy_group))

@task
def staging():
    env.environment = 'staging'
    set_variables()

    env.hosts = ['support-tools-staging-1.vpc3.10gen.cc']

def set_variables():
    env.deploy_name  = app + '-' + env.environment
    env.deploy_group = group + '-' + env.environment
    env.base_dir     = os.path.join('/opt/10gen', env.deploy_name)
    env.current_link = os.path.join(env.base_dir, 'current')
    env.scripts_link = os.path.join(env.base_dir, 'scripts')
    env.releases_dir = os.path.join(env.base_dir, 'releases')
    env.init = '/etc/init.d'

@task
def deploy():
    set_variables()

    projects = {
        'karakuri': {
            'requirements': os.path.join(env.current_link, 'karakuri', 'requirements.txt'),
            'config':       os.path.join(env.current_link, 'karakuri', 'karakuri.cfg'),
            'init':         os.path.join(env.init, 'karakuri')
        },
        'karakurid': {
            'config':       os.path.join(env.current_link, 'karakuri', 'karakurid.cfg'),
            'init':         os.path.join(env.init, 'karakurid')
        },
        'euphonia': {
            'requirements': os.path.join(env.current_link, 'euphonia', 'requirements.txt'),
            'config':       os.path.join(env.current_link, 'euphonia', 'euphonia.cfg'),
            'init':         os.path.join(env.init, 'euphonia')
        }
    }

    now = time.strftime(datetime_format)
    deploy_dir       = os.path.join(env.releases_dir, now)

    scl = 'scl enable python27'
    virtualenv_dir = os.path.join(env.base_dir, 'virtualenv')
    virtualenv_pip = os.path.join(virtualenv_dir, 'bin/pip')

    run('git clone {0} {1}'.format(repo, deploy_dir))
    run('chmod 2775 {0}'.format(deploy_dir))

    # update the current deployment symlink
    run('ln -sfn {0} {1}'.format(deploy_dir, env.current_link))

    for p in projects:
        project = projects[p]

        # config file symlink
        if 'config' in project:
            path, filename = os.path.split(project['config'])
            run('ln -sfn {0} {1}'.format(os.path.join(env.base_dir, filename), path))

        # install requirements
        if 'requirements' in project:
            run("{0} '{1} install -r {2}'".format(
                scl,
                virtualenv_pip,
                project['requirements']
                ))

        # restart service
        if 'init' in project:
            run('sudo {0} restart'.format(project['init']))

