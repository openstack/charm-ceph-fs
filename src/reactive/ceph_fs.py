import os
import subprocess
import json

from charms.reactive import when, when_not, set_state

from charms.apt import queue_install

from charmhelpers.core.hookenv import (
    config, charm_name,
    log, INFO, ERROR)

from charmhelpers.core.host import service_restart

from charmhelpers.contrib.network.ip import (
    get_address_in_network
)

import jinja2

TEMPLATES_DIR = 'templates'


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)

@when_not('apt.installed.ceph-mds')
def install_cephfs():
    queue_install(['ceph-mds'])


@when('apt.installed.ceph-mds', 'ceph.installed')
@when_not('cephfs.started')
def setup_mds():
    log("I'm in setup_mds()")
    # try:
    #     from rados import Error as RadosError
    #     from ceph_api import ceph_command
    # except ImportError as err:
    #     log("rados is not installed yet: {}".format(err))
    #     return
    # TODO: Monitor needs a new CephFS relation
    # TODO: Update with the conf file location
    # osd = ceph_command.OsdCommand('/etc/ceph/ceph.conf')
    # mds = ceph_command.MdsCommand('/etc/ceph/ceph.conf')

    try:
        name = charm_name()
        log("Creating cephfs_data pool", level=INFO)
        data_pool = "{}_data".format(name)
        # TODO: Update with better pg values
        try:
            subprocess.check_call(["ceph", "osd", "pool", "create", data_pool, "256"])
        except subprocess.CalledProcessError as err:
            log("Creating data pool failed!")
            raise(err)
        # osd.osd_pool_create('cephfs_data', 256)

        log("Creating cephfs_metadata pool", level=INFO)
        metadata_pool = "{}_metadata".format(name)
        # TODO: Update with better pg values
        try:
            subprocess.check_call(["ceph", "osd", "pool", "create", metadata_pool, "256"])
        except subprocess.CalledProcessError as err:
            log("Creating metadata pool failed!")
            raise(err)
        # osd.osd_pool_create('cephfs_metadata', 256)

        log("Creating ceph fs", level=INFO)
        try:
            subprocess.check_call(["ceph", "fs", "new", name, metadata_pool, data_pool])
        except subprocess.CalledProcessError as err:
            log("Creating metadata pool failed!")
            raise(err)
        service_restart('ceph-mds')
        set_state('cephfs.started')
        # mds.mds_newfs(metadata='cephfs_metadata', data='cephfs_data', sure=["--yes-i-really-mean-it"])
    except subprocess.CalledProcessError as err:
        log(message='Error: {}'.format(err), level=ERROR)


@when('ceph-admin.available')
# @when_not('cephfs.configured')
def config_changed(ceph_client):
    charm_ceph_conf = os.path.join(os.sep,
                                   'etc',
                                   'ceph',
                                   'ceph.conf')
    cephx_key = os.path.join(os.sep,
                             'etc',
                             'ceph',
                             'ceph.client.admin.keyring')

    networks = get_networks('ceph-public-network')
    public_network = ', '.join(networks)

    networks = get_networks('ceph-cluster-network')
    cluster_network = ', '.join(networks)

    ceph_context = {
        'mon_hosts': ceph_client.mon_hosts(),
        'fsid': ceph_client.fsid(),
        'auth_supported': ceph_client.auth(),
        'use_syslog': str(config('use-syslog')).lower(),
        'ceph_public_network': public_network,
        'ceph_cluster_network': cluster_network,
        'loglevel': config('loglevel'),
    }

    try:
        with open(charm_ceph_conf, 'w') as ceph_conf:
            ceph_conf.write(render_template('ceph.conf', ceph_context))
    except IOError as err:
        log("IOError writing ceph.conf: {}".format(err))

    try:
        with open(cephx_key, 'w') as key_file:
            key_file.write("[client.admin]\n\tkey = {}\n".format(
                ceph_client.key()
            ))
    except IOError as err:
        log("IOError writing ceph.client.admin.keyring: {}".format(err))
    set_state('cephfs.configured')


def get_networks(config_opt='ceph-public-network'):
    """Get all configured networks from provided config option.

    If public network(s) are provided, go through them and return those for
    which we have an address configured.
    """
    networks = config(config_opt)
    if networks:
        networks = networks.split()
        return [n for n in networks if get_address_in_network(n)]

    return []
