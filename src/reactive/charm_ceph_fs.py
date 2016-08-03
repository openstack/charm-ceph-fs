from charms.reactive import when

from charmhelpers.core.hookenv import (
    config,
    log, INFO, ERROR)

from charmhelpers.contrib.network.ip import (
    get_address_in_network
)

@when('ceph.installed')
# @when('ceph-mon.available')
def setup_mds(mon):
    log("I'm in setup_mds()")
    try:
        from rados import Error as RadosError
        from ceph_api import ceph_command
    except ImportError as err:
        log("rados is not installed yet: {}".format(err))
        return
    # TODO: Monitor needs a new CephFS relation
    # TODO: Update with the conf file location
    osd = ceph_command.OsdCommand('/etc/ceph/ceph.conf')
    mds = ceph_command.MdsCommand('/etc/ceph/ceph.conf')

    try:
        log("Creating cephfs_data pool", level=INFO)
        # TODO: Update with better pg values
        osd.osd_pool_create('cephfs_data', 256)

        log("Creating cephfs_metadata pool", level=INFO)
        # TODO: Update with better pg values
        osd.osd_pool_create('cephfs_metadata', 256)

        log("Creating ceph fs", level=INFO)
        mds.mds_newfs(metadata='cephfs_metadata', data='cephfs_data', sure=["--yes-i-really-mean-it"])
    except RadosError as err:
        log(message='Error: {}'.format(err.message), level=ERROR)


@when('config.changed', 'ceph-mon.available')
def config_changed():
    networks = get_networks('ceph-public-network')
    public_network = ', '.join(networks)

    networks = get_networks('ceph-cluster-network')
    cluster_network = ', '.join(networks)

    cephcontext = {
        # 'mon_hosts': ' '.join(get_mon_hosts()),
        # 'fsid': leader_get('fsid'),
        'osd_journal_size': config('osd-journal-size'),
        'use_syslog': str(config('use-syslog')).lower(),
        'ceph_public_network': public_network,
        'ceph_cluster_network': cluster_network,
        'loglevel': config('loglevel'),
    }


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
