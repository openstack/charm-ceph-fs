# Copyright 2020 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import socket

import dns.resolver

import charms_openstack.adapters
import charms_openstack.charm
import charms_openstack.plugins

import charmhelpers.core as ch_core

# NOTE(fnordahl) theese out of style imports are here to help keeping helpers
# moved from reactive module as-is to make the diff managable. At some point
# in time we should replace them in favor of common helpers that would do the
# same job.
from charmhelpers.core.hookenv import (
    config, log, cached, DEBUG, unit_get,
    network_get_primary_address,
    status_set)
from charmhelpers.contrib.network.ip import (
    get_address_in_network,
    get_ipv6_addr)


charms_openstack.charm.use_defaults('charm.default-select-release')


class CephFSCharmConfigurationAdapter(
        charms_openstack.adapters.ConfigurationAdapter):

    @property
    def hostname(self):
        return self.charm_instance.hostname

    @property
    def mds_name(self):
        return self.charm_instance.hostname

    @property
    def networks(self):
        return self.charm_instance.get_networks('ceph-public-network')

    @property
    def public_addr(self):
        if ch_core.hookenv.config('prefer-ipv6'):
            return get_ipv6_addr()[0]
        else:
            return self.charm_instance.get_public_addr()


class CephFSCharmRelationAdapters(
        charms_openstack.adapters.OpenStackRelationAdapters):
    relation_adapters = {
        'ceph-mds': charms_openstack.plugins.CephRelationAdapter,
    }


class BaseCephFSCharm(charms_openstack.plugins.CephCharm):
    abstract_class = True
    name = 'ceph-fs'
    python_version = 3
    required_relations = ['ceph-mds']
    user = 'ceph'
    group = 'ceph'
    adapters_class = CephFSCharmRelationAdapters
    configuration_class = CephFSCharmConfigurationAdapter
    ceph_service_type = charms_openstack.plugins.CephCharm.CephServiceType.mds
    ceph_service_name_override = 'mds'
    ceph_key_per_unit_name = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.services = [
            'ceph-mds@{}'.format(self.hostname),
        ]
        self.restart_map = {
            '/etc/ceph/ceph.conf': self.services,
        }

    # NOTE(fnordahl) moved from reactive handler module, otherwise keeping
    # these as-is to make the diff managable. At some point in time we should
    # replace them in favor of common helpers that would do the same job.
    @staticmethod
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

    @cached
    def get_public_addr(self):
        if config('ceph-public-network'):
            return self.get_network_addrs('ceph-public-network')[0]

        try:
            return network_get_primary_address('public')
        except NotImplementedError:
            log("network-get not supported", DEBUG)

        return self.get_host_ip()

    @cached
    @staticmethod
    def get_host_ip(hostname=None):
        if config('prefer-ipv6'):
            return get_ipv6_addr()[0]

        hostname = hostname or unit_get('private-address')
        try:
            # Test to see if already an IPv4 address
            socket.inet_aton(hostname)
            return hostname
        except socket.error:
            # This may throw an NXDOMAIN exception; in which case
            # things are badly broken so just let it kill the hook
            answers = dns.resolver.query(hostname, 'A')
            if answers:
                return answers[0].address

    def get_network_addrs(self, config_opt):
        """Get all configured public networks addresses.

        If public network(s) are provided, go through them and return the
        addresses we have configured on any of those networks.
        """
        addrs = []
        networks = config(config_opt)
        if networks:
            networks = networks.split()
            addrs = [get_address_in_network(n) for n in networks]
            addrs = [a for a in addrs if a]

        if not addrs:
            if networks:
                msg = ("Could not find an address on any of '%s' - resolve "
                       "this error to retry" % networks)
                status_set('blocked', msg)
                raise Exception(msg)
            else:
                return [self.get_host_ip()]

        return addrs


class MitakaCephFSCharm(BaseCephFSCharm):
    release = 'mitaka'
    packages = ['ceph-mds', 'gdisk', 'btrfs-tools', 'xfsprogs']


class UssuriCephFSCharm(BaseCephFSCharm):
    release = 'ussuri'
    packages = ['ceph-mds', 'gdisk', 'btrfs-progs', 'xfsprogs']
