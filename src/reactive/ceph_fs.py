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
    application_version_set, config, log, ERROR)
from charmhelpers.core.host import service_restart
from charmhelpers.contrib.network.ip import (
    get_address_in_network
)
from charmhelpers.fetch import (
    get_upstream_version,
)

import jinja2

from charms.apt import queue_install

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
