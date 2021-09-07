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

import unittest.mock as mock

import charms_openstack.test_utils as test_utils

import charm.openstack.ceph_fs as ceph_fs


class TestMitakaCephFsCharm(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release('mitaka')
        self.patch('socket.gethostname', name='gethostname')
        self.gethostname.return_value = 'somehost'
        self.target = ceph_fs.MitakaCephFSCharm()

    def test_packages(self):
        # Package list is the only difference between the past version and
        # future versions of this charm, see ``TestCephFsCharm`` for the rest
        # of the tests
        self.assertEquals(self.target.packages, [
            'ceph-mds', 'gdisk', 'btrfs-tools', 'xfsprogs'])


class TestCephFsCharm(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release('ussuri')
        self.patch('socket.gethostname', name='gethostname')
        self.gethostname.return_value = 'somehost'
        self.target = ceph_fs.UssuriCephFSCharm()

    def patch_target(self, attr, return_value=None):
        mocked = mock.patch.object(self.target, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test___init__(self):
        self.assertEquals(self.target.services, [
            'ceph-mds@somehost'])
        self.assertDictEqual(self.target.restart_map, {
            '/etc/ceph/ceph.conf': ['ceph-mds@somehost']})
        self.assertEquals(self.target.packages, [
            'ceph-mds', 'gdisk', 'btrfs-progs', 'xfsprogs'])

    def test_configuration_class(self):
        self.assertEquals(self.target.options.hostname, 'somehost')
        self.assertEquals(self.target.options.mds_name, 'somehost')
        self.patch_target('get_networks')
        self.get_networks.return_value = ['fakeaddress']
        self.assertEquals(self.target.options.networks, ['fakeaddress'])
        self.patch_object(ceph_fs.ch_core.hookenv, 'config')
        self.config.side_effect = lambda x: {'prefer-ipv6': False}.get(x)
        self.patch_object(ceph_fs, 'get_ipv6_addr')
        self.get_ipv6_addr.return_value = ['2001:db8::fake']
        self.patch_target('get_public_addr')
        self.get_public_addr.return_value = '192.0.2.42'
        self.assertEquals(
            self.target.options.public_addr,
            '192.0.2.42')
        self.config.side_effect = lambda x: {'prefer-ipv6': True}.get(x)
        self.assertEquals(
            self.target.options.public_addr,
            '2001:db8::fake')
