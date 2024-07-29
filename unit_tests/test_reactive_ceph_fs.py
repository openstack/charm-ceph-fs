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
                'config_changed': (
                    'ceph-mds.pools.available',
                ),
                'storage_ceph_connected': (
                    'ceph-mds.connected',
                ),
                'cephfs_share_available': (
                    'cephfs.configured',
                    'ceph-mds.pools.available',
                    'cephfs-share.available',
                ),
            },
            'when_none': {
                'config_changed': (
                    'charm.paused',
                    'is-update-status-hook',
                ),
                'storage_ceph_connected': (
                    'charm.paused',
                    'is-update-status-hook',
                ),
                'cephfs_share_available': (
                    'charm.paused',
                    'is-update-status-hook',
                ),
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
        self.patch_object(handlers.os.path, 'exists')
        handlers.os.path.exists.return_value = False
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

    def test_cephfs_share_available(self):
        self.patch_object(handlers.reactive, 'endpoint_from_flag')
        handlers.ch_core.hookenv.application_name.return_value = "ceph-fs"
        handlers.ceph.get_broker_rsp_key.return_value = 'broker-rsp-ceph-fs-0'

        ceph_mds = mock.MagicMock()
        ceph_mds.fsid = "354ca7c4-f10d-11ee-93f8-1f85f87b7845"
        ceph_mds.mon_hosts.return_value = [
            "10.5.0.80:6789", "10.5.2.23:6789", "10.5.2.17:6789"]
        ceph_mds.all_joined_units.received = {
            "auth": "cephx",
            "broker-rsp-ceph-fs-0": {
                "exit-code": 0,
                "key": "AQDvOE5mUfBIKxAAYT73/v7NzwWx2ovLB4nnOg==",
                "request-id": "22dd9c7d8c7d392d44866b35219a654006fd90f0"},
            "ceph-public-address": "10.143.60.15",
            "fsid": "354ca7c4-f10d-11ee-93f8-1f85f87b7845",
            "juju-2ffa43-1_mds_key":
                "AQDwOE5mmkQ1LBAAVrx4OXWwWM+XmK/KjnJcdA==",
        }

        cephfs_share = mock.MagicMock()

        def mock_eff(flag):
            if flag == "ceph-mds.pools.available":
                return ceph_mds
            elif flag == "cephfs-share.available":
                return cephfs_share
            else:
                raise Exception("invalid input")

        self.endpoint_from_flag.side_effect = mock_eff

        handlers.cephfs_share_available()

        cephfs_share.set_share.assert_called_once_with(
            share_info={
                "fsid": "354ca7c4-f10d-11ee-93f8-1f85f87b7845",
                "name": "ceph-fs",
                "path": "/",
                "monitor_hosts": [
                    "10.5.0.80:6789",
                    "10.5.2.23:6789",
                    "10.5.2.17:6789"
                ],
            },
            auth_info={
                "username": "ceph-fs-client",
                "key": "AQDvOE5mUfBIKxAAYT73/v7NzwWx2ovLB4nnOg=="
            }
        )
