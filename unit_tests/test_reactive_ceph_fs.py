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

import charm.openstack.ceph_fs as ceph_fs
import reactive.ceph_fs as handlers

import charms_openstack.test_utils as test_utils


class TestRegisteredHooks(test_utils.TestRegisteredHooks):

    def test_hooks(self):
        defaults = [
            'charm.installed',
            'config.changed',
            'config.rendered',
            'upgrade-charm',
            'update-status',
        ]
        hook_set = {
            'when': {
                'config_changed': ('ceph-mds.pools.available',),
                'storage_ceph_connected': ('ceph-mds.connected',),
            },
            'when_none': {
                'config_changed': ('charm.paused',
                                   'run-default-update-status',),
            },
        }
        # test that the hooks were registered via the reactive.ceph_fs module
        self.registered_hooks_test_helper(handlers, hook_set, defaults)


class TestCephFSHandlers(test_utils.PatchHelper):

    def setUp(self):
        super().setUp()
        self.patch_release(ceph_fs.UssuriCephFSCharm.release)
        self.target = mock.MagicMock()
        self.patch_object(handlers.charm, 'provide_charm_instance',
                          new=mock.MagicMock())
        self.provide_charm_instance().__enter__.return_value = \
            self.target
        self.provide_charm_instance().__exit__.return_value = None

    def test_config_changed(self):
        self.patch_object(handlers.reactive, 'endpoint_from_flag')
        self.patch_object(handlers.reactive, 'is_flag_set')
        self.patch_object(handlers.reactive, 'clear_flag')
        self.patch_object(handlers.reactive, 'set_flag')
        ceph_mds = mock.MagicMock()
        ceph_mds.mds_key.return_value = 'fakekey'
        self.endpoint_from_flag.return_value = ceph_mds
        self.is_flag_set.return_value = False
        handlers.config_changed()
        self.endpoint_from_flag.assert_called_once_with(
            'ceph-mds.pools.available')
        self.target.configure_ceph_keyring.assert_called_once_with('fakekey')
        self.target.render_with_interfaces.assert_called_once_with([ceph_mds])
        self.is_flag_set.assert_called_once_with('config.changed.source')
        self.set_flag.assert_has_calls([
            mock.call('cephfs.configured'),
            mock.call('config.rendered'),
        ])
        self.target.install.assert_not_called()
        self.target.upgrade_if_available.assert_not_called()
        self.is_flag_set.return_value = True
        handlers.config_changed()
        self.target.install.assert_called_once_with()
        self.target.upgrade_if_available.assert_called_once_with([ceph_mds])
