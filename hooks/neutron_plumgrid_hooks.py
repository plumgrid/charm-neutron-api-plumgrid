#!/usr/bin/python

# Copyright (c) 2015, PLUMgrid Inc, http://plumgrid.com

# The hooks of this charm have been symlinked to functions
# in this file.

import sys
from charmhelpers.core.hookenv import (
    Hooks,
    UnregisteredHookError,
    log,
    config,
    status_set
)

from charmhelpers.core.host import (
    restart_on_change,
    service_start,
    service_stop,
    service_running
)

from charmhelpers.fetch import (
    apt_install,
    apt_update,
    configure_sources,
)

from neutron_plumgrid_utils import (
    determine_packages,
    register_configs,
    restart_map,
    ensure_files,
    set_neutron_relation,
    configure_pg_sources
)

hooks = Hooks()
CONFIGS = register_configs()


@hooks.hook()
def install():
    '''
    Install hook is run when the charm is first deployed on a node.
    '''
    status_set('maintenance', 'Executing pre-install')
    configure_sources()
    status_set('maintenance', 'Installing apt packages')
    apt_update()
    pkgs = determine_packages()
    for pkg in pkgs:
        apt_install(pkg, options=['--force-yes'], fatal=True)
    ensure_files()


@hooks.hook('config-changed')
@restart_on_change(restart_map())
def config_changed():
    '''
    This hook is run when a config parameter is changed.
    It also runs on node reboot.
    '''
    charm_config = config()
    if (charm_config.changed('install_sources') or
        charm_config.changed('plumgrid-build') or
        charm_config.changed('networking-build') or
            charm_config.changed('install_keys')):
        status_set('maintenance', 'Upgrading apt packages')
        if charm_config.changed('install_sources'):
            configure_pg_sources()
        configure_sources()
        apt_update()
        pkgs = determine_packages()
        for pkg in pkgs:
            apt_install(pkg, options=['--force-yes'], fatal=True)
        service_stop('neutron-server')
    if (charm_config.changed('networking-plumgrid-version') or
            charm_config.changed('pip-proxy')):
        ensure_files()
        service_stop('neutron-server')
    CONFIGS.write_all()
    if not service_running('neutron-server'):
        service_start('neutron-server')
    status_set('active', 'Unit is ready')


@hooks.hook('neutron-plugin-api-relation-joined')
@hooks.hook('plumgrid-plugin-relation-changed')
@hooks.hook('container-relation-changed')
@restart_on_change(restart_map())
def relation_changed():
    '''
    This hook is run when relation between neutron-api-plumgrid and
    neutron-api or plumgrid-edge is made.
    '''
    ensure_files()
    CONFIGS.write_all()


@hooks.hook("neutron-plugin-api-subordinate-relation-joined")
def neutron_plugin_joined():
    set_neutron_relation()


@hooks.hook("plumgrid-configs-relation-changed")
@restart_on_change(restart_map())
def plumgrid_configs_relation():
    CONFIGS.write_all()


@hooks.hook("identity-admin-relation-changed")
@restart_on_change(restart_map())
def identity_admin_relation():
    CONFIGS.write_all()


@hooks.hook('stop')
def stop():
    '''
    This hook is run when the charm is destroyed.
    '''
    log('Charm stopping without removal of packages')


@hooks.hook('update-status')
def update_status():
    if service_running('neutron-server'):
        status_set('active', 'Unit is ready')
    else:
        status_set('blocked', 'neutron server not running')


def main():
    try:
        hooks.execute(sys.argv)
    except UnregisteredHookError as e:
        log('Unknown hook {} - skipping.'.format(e))


if __name__ == '__main__':
    main()
