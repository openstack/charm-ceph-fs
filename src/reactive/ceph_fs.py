# Copyright 2016 Canonical Ltd
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

import os
import socket
import subprocess

from charms.reactive import when, when_not, set_state
from charmhelpers.core.hookenv import (
    application_version_set, config, log, ERROR, cached, DEBUG, unit_get,
    network_get_primary_address,
    status_set)
from charmhelpers.core.host import service_restart
from charmhelpers.contrib.network.ip import (
    get_address_in_network,
    get_ipv6_addr)

from charmhelpers.fetch import (
    get_upstream_version,
    apt_install, filter_installed_packages)
import jinja2

from charms.apt import queue_install

try:
    import dns.resolver
except ImportError:
    apt_install(filter_installed_packages(['python-dnspython']),
                fatal=True)
    import dns.resolver
TEMPLATES_DIR = 'templates'
VERSION_PACKAGE = 'ceph-common'


def render_template(template_name, context, template_dir=TEMPLATES_DIR):
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir))
    template = templates.get_template(template_name)
    return template.render(context)


@when_not('apt.installed.ceph-mds')
def install_cephfs():
    queue_install(['ceph-mds'])


@when('cephfs.configured')
@when('ceph-mds.pools.available')
@when_not('cephfs.started')
def setup_mds(relation):
    try:
        service_restart('ceph-mds')
        set_state('cephfs.started')
        application_version_set(get_upstream_version(VERSION_PACKAGE))
    except subprocess.CalledProcessError as err:
        log(message='Error: {}'.format(err), level=ERROR)


@when('ceph-mds.available')
def config_changed(ceph_client):
    charm_ceph_conf = os.path.join(os.sep,
                                   'etc',
                                   'ceph',
                                   'ceph.conf')
    key_path = os.path.join(os.sep,
                            'var',
                            'lib',
                            'ceph',
                            'mds',
                            'ceph-{}'.format(socket.gethostname())
                            )
    if not os.path.exists(key_path):
        os.makedirs(key_path)
    cephx_key = os.path.join(key_path,
                             'keyring')

    ceph_context = {
        'fsid': ceph_client.fsid(),
        'auth_supported': ceph_client.auth(),
        'use_syslog': str(config('use-syslog')).lower(),
        'mon_hosts': ' '.join(ceph_client.mon_hosts()),
        'loglevel': config('loglevel'),
        'hostname': socket.gethostname(),
        'mds_name': socket.gethostname(),
    }

    networks = get_networks('ceph-public-network')
    if networks:
        ceph_context['ceph_public_network'] = ', '.join(networks)
    elif config('prefer-ipv6'):
        dynamic_ipv6_address = get_ipv6_addr()[0]
        ceph_context['public_addr'] = dynamic_ipv6_address
    else:
        ceph_context['public_addr'] = get_public_addr()

    try:
        with open(charm_ceph_conf, 'w') as ceph_conf:
            ceph_conf.write(render_template('ceph.conf', ceph_context))
    except IOError as err:
        log("IOError writing ceph.conf: {}".format(err))

    try:
        with open(cephx_key, 'w') as key_file:
            key_file.write("[mds.{}]\n\tkey = {}\n".format(
                socket.gethostname(),
                ceph_client.mds_key()
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


@cached
def get_public_addr():
    if config('ceph-public-network'):
        return get_network_addrs('ceph-public-network')[0]

    try:
        return network_get_primary_address('public')
    except NotImplementedError:
        log("network-get not supported", DEBUG)

    return get_host_ip()


@cached
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


def get_network_addrs(config_opt):
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
            msg = ("Could not find an address on any of '%s' - resolve this "
                   "error to retry" % networks)
            status_set('blocked', msg)
            raise Exception(msg)
        else:
            return [get_host_ip()]

    return addrs
