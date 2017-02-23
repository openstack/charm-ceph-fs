#!/usr/bin/env python
#
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

import amulet

from charmhelpers.contrib.openstack.amulet.deployment import (
    OpenStackAmuletDeployment
)
from charmhelpers.contrib.openstack.amulet.utils import (  # noqa
    OpenStackAmuletUtils,
    DEBUG,
    )

# Use DEBUG to turn on debug logging
u = OpenStackAmuletUtils(DEBUG)


class CephFsBasicDeployment(OpenStackAmuletDeployment):
    """Amulet tests on a basic ceph deployment."""

    def __init__(self, series=None, openstack=None, source=None, stable=True):
        """Deploy the entire test environment."""
        super(CephFsBasicDeployment, self).__init__(series,
                                                    openstack,
                                                    source,
                                                    stable)
        self._add_services()
        self._add_relations()
        self._configure_services()
        self._deploy()

        u.log.info('Waiting on extended status checks...')
        exclude_services = []

        # Wait for deployment ready msgs, except exclusions
        self._auto_wait_for_status(exclude_services=exclude_services)

        self.d.sentry.wait()
        self._initialize_tests()

    def _add_services(self, **kwargs):
        """Add services

           Add the services that we're testing, where cephfs is local,
           and the rest of the service are from lp branches that are
           compatible with the local charm (e.g. stable or next).
        :param **kwargs:
           """
        this_service = {'name': 'ceph-fs', 'units': 1}
        other_services = [
            {'name': 'ceph-mon', 'units': 3},
            {'name': 'ceph-osd', 'units': 3},
        ]
        super(CephFsBasicDeployment, self)._add_services(this_service,
                                                         other_services)

    def _add_relations(self, **kwargs):
        """Add all of the relations for the services.
        :param **kwargs:
        """
        relations = {
            'ceph-osd:mon': 'ceph-mon:osd',
            'ceph-fs:ceph-mds': 'ceph-mon:mds',
        }
        super(CephFsBasicDeployment, self)._add_relations(relations)

    def _configure_services(self, **kwargs):
        """Configure all of the services.
        :param **kwargs:
        """
        # NOTE(jamespage): fix fsid to allow later validation
        ceph_mon_config = {
            'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
        }
        # Include a non-existent device as osd-devices is a whitelist,
        # and this will catch cases where proposals attempt to change that.
        ceph_osd_config = {
            'osd-reformat': 'yes',
            'ephemeral-unmount': '/mnt',
            'osd-devices': '/dev/vdb /srv/ceph /dev/test-non-existent'
        }

        configs = {
            'ceph-mon': ceph_mon_config,
            'ceph-osd': ceph_osd_config}
        super(CephFsBasicDeployment, self)._configure_services(configs)

    def _initialize_tests(self):
        """Perform final initialization before tests get run."""
        # Access the sentries for inspecting service units
        self.ceph_osd0_sentry = self.d.sentry['ceph-osd'][0]
        self.ceph_osd1_sentry = self.d.sentry['ceph-osd'][1]
        self.ceph_osd2_sentry = self.d.sentry['ceph-osd'][2]

        self.ceph_mon0_sentry = self.d.sentry['ceph-mon'][0]
        self.ceph_mon1_sentry = self.d.sentry['ceph-mon'][1]
        self.ceph_mon2_sentry = self.d.sentry['ceph-mon'][2]

        self.ceph_mds_sentry = self.d.sentry['ceph-fs'][0]

    def test_100_ceph_processes(self):
        """Verify that the expected service processes are running
        on each ceph unit."""

        # Process name and quantity of processes to expect on each unit
        ceph_mon_processes = {
            'ceph-mon': 1
        }
        ceph_osd_processes = {
            'ceph-osd': 2
        }
        ceph_mds_processes = {
            'ceph-mds': 1
        }

        # Units with process names and PID quantities expected
        expected_processes = {
            self.ceph_mon0_sentry: ceph_mon_processes,
            self.ceph_mon1_sentry: ceph_mon_processes,
            self.ceph_mon2_sentry: ceph_mon_processes,
            self.ceph_osd0_sentry: ceph_osd_processes,
            self.ceph_osd1_sentry: ceph_osd_processes,
            self.ceph_osd2_sentry: ceph_osd_processes,
            self.ceph_mds_sentry: ceph_mds_processes
        }

        actual_pids = u.get_unit_process_ids(expected_processes)
        ret = u.validate_unit_process_ids(expected_processes, actual_pids)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_102_services(self):
        """Verify the expected services are running on the service units."""
        services = {}

        if self._get_openstack_release() < self.xenial_mitaka:
            # For upstart systems only.  Ceph services under systemd
            # are checked by process name instead.
            ceph_services = [
                'ceph-mon-all',
                'ceph-mon id=`hostname`'
            ]
            services[self.ceph_mon0_sentry] = ceph_services
            services[self.ceph_mon1_sentry] = ceph_services
            services[self.ceph_mon2_sentry] = ceph_services

            ceph_osd_services = [
                'ceph-osd id={}'.format(u.get_ceph_osd_id_cmd(0)),
            ]

            services[self.ceph_osd0_sentry] = ceph_osd_services

        ret = u.validate_services_by_name(services)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

    def test_300_ceph_config(self):
        """Verify the data in the ceph config file."""
        u.log.debug('Checking ceph config file data...')
        unit = self.ceph_mon0_sentry
        conf = '/etc/ceph/ceph.conf'
        expected = {
            'global': {
                'keyring': '/etc/ceph/$cluster.$name.keyring',
                'fsid': '6547bd3e-1397-11e2-82e5-53567c8d32dc',
                'log to syslog': 'false',
                'err to syslog': 'false',
                'clog to syslog': 'false',
                'mon cluster log to syslog': 'false',
                'auth cluster required': 'cephx',
                'auth service required': 'cephx',
                'auth client required': 'cephx'
            },
            'mon': {
                'keyring': '/var/lib/ceph/mon/$cluster-$id/keyring'
            },
            'mds': {
                'keyring': '/var/lib/ceph/mds/$cluster-$id/keyring'
            },
        }

        for section, pairs in expected.iteritems():
            ret = u.validate_config_data(unit, conf, section, pairs)
            if ret:
                message = "ceph config error: {}".format(ret)
                amulet.raise_status(amulet.FAIL, msg=message)

    def test_400_ceph_check_osd_pools(self):
        """Check osd pools on all ceph units, expect them to be
        identical, and expect specific pools to be present."""
        u.log.debug('Checking pools on ceph units...')
        expected_pools = ['rbd', 'ceph-fs_data', 'ceph-fs_metadata']
        results = []
        sentries = [
            self.ceph_mon0_sentry,
            self.ceph_mon1_sentry,
            self.ceph_mon2_sentry
        ]

        # Check for presence of expected pools on each unit
        u.log.debug('Expected pools: {}'.format(expected_pools))
        for sentry_unit in sentries:
            pools = u.get_ceph_pools(sentry_unit)
            results.append(pools)

            for expected_pool in expected_pools:
                if expected_pool not in pools:
                    msg = ('{} does not have pool: '
                           '{}'.format(sentry_unit.info['unit_name'],
                                       expected_pool))
                    amulet.raise_status(amulet.FAIL, msg=msg)
            u.log.debug('{} has (at least) the expected '
                        'pools.'.format(sentry_unit.info['unit_name']))

        # Check that all units returned the same pool name:id data
        ret = u.validate_list_of_identical_dicts(results)
        if ret:
            u.log.debug('Pool list results: {}'.format(results))
            msg = ('{}; Pool list results are not identical on all '
                   'ceph units.'.format(ret))
            amulet.raise_status(amulet.FAIL, msg=msg)
        else:
            u.log.debug('Pool list on all ceph units produced the '
                        'same results (OK).')

    def test_499_ceph_cmds_exit_zero(self):
        """Check basic functionality of ceph cli commands against
        all ceph units."""
        sentry_units = [
            self.ceph_mon0_sentry,
            self.ceph_mon1_sentry,
            self.ceph_mon2_sentry
        ]
        commands = [
            'sudo ceph health',
            'sudo ceph mds stat',
            'sudo ceph pg stat',
            'sudo ceph osd stat',
            'sudo ceph mon stat',
            'sudo ceph fs ls',
        ]
        ret = u.check_commands_on_units(commands, sentry_units)
        if ret:
            amulet.raise_status(amulet.FAIL, msg=ret)

            # FYI: No restart check as ceph services do not restart
            # when charm config changes, unless monitor count increases.
