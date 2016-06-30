from charms.reactive import when, when_not, set_state

from charmhelpers.core.hookenv import (
    config,
)

from charmhelpers.contrib.network.ip import (
    get_address_in_network
)

@when('ceph.installed')
@when('ceph-mon.available')
def setup_mds(mon):
    

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
