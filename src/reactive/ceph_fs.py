import os
import socket
import subprocess

from charms.reactive import when, when_not, set_state
from charmhelpers.core.hookenv import (
    config, charm_name,
    log, INFO, ERROR)
from charmhelpers.core.host import service_restart
from charmhelpers.contrib.storage.linux import ceph
from charmhelpers.contrib.network.ip import (
    get_address_in_network
)
import jinja2

from charms.apt import queue_install

TEMPLATES_DIR = 'templates'


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)


@when_not('apt.installed.ceph-mds')
def install_cephfs():
    queue_install(['ceph-mds'])


@when('cephfs.configured')
@when('admin_key.saved')
@when_not('cephfs.started')
def setup_mds():
    try:
        name = charm_name()
        log("Creating cephfs_data pool", level=INFO)
        data_pool = "{}_data".format(name)
        try:
            ceph.ReplicatedPool(name=data_pool, service='admin').create()
        except subprocess.CalledProcessError as err:
            log("Creating data pool failed!")
            raise err

        log("Creating cephfs_metadata pool", level=INFO)
        metadata_pool = "{}_metadata".format(name)
        try:
            ceph.ReplicatedPool(name=metadata_pool, service='admin').create()
        except subprocess.CalledProcessError as err:
            log("Creating metadata pool failed!")
            raise err

        log("Creating ceph fs", level=INFO)
        try:
            subprocess.check_call(["ceph", "fs", "new", name, metadata_pool, data_pool])
        except subprocess.CalledProcessError as err:
            log("Creating metadata pool failed!")
            raise err
        service_restart('ceph-mds')
        set_state('cephfs.started')
    except subprocess.CalledProcessError as err:
        log(message='Error: {}'.format(err), level=ERROR)


@when('ceph-admin.available')
def handle_admin_key(ceph_client):
    cephx_key = os.path.join(os.sep,
                             'etc',
                             'ceph',
                             'ceph.client.admin.keyring')
    try:
        with open(cephx_key, 'w') as key_file:
            key_file.write("[client.admin]\n\tkey = {}\n".format(
                ceph_client.key()
            ))
    except IOError as err:
        log("IOError writing mds-a.keyring: {}".format(err))
    set_state('admin_key.saved')


@when('ceph-mds.available')
def config_changed(ceph_client):
    charm_ceph_conf = os.path.join(os.sep,
                                   'etc',
                                   'ceph',
                                   'ceph.conf')
    key_path = os.path.join(os.sep, 'var', 'lib', 'ceph', 'mds', 'ceph-a')
    if not os.path.exists(key_path):
        os.makedirs(key_path)
    cephx_key = os.path.join(key_path,
                             'keyring')

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
        'hostname': socket.gethostname(),
        'mds_name': 'a',
    }

    try:
        with open(charm_ceph_conf, 'w') as ceph_conf:
            ceph_conf.write(render_template('ceph.conf', ceph_context))
    except IOError as err:
        log("IOError writing ceph.conf: {}".format(err))

    try:
        with open(cephx_key, 'w') as key_file:
            key_file.write("[mds.a]\n\tkey = {}\n".format(
                ceph_client.key()
            ))
    except IOError as err:
        log("IOError writing mds-a.keyring: {}".format(err))
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
