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

from charms import reactive

import charms_openstack.bus
import charms_openstack.charm as charm


charms_openstack.bus.discover()


charm.use_defaults(
    'charm.installed',
    'config.changed',
    'config.rendered',
    'upgrade-charm',
    'update-status',
)


@reactive.when_none('charm.paused', 'run-default-update-status')
@reactive.when('ceph-mds.available')
def config_changed():
    ceph_mds = reactive.endpoint_from_flag('ceph-mds.available')
    with charm.provide_charm_instance() as cephfs_charm:
        cephfs_charm.configure_ceph_keyring(ceph_mds.mds_key())
        cephfs_charm.render_with_interfaces([ceph_mds])
        if reactive.is_flag_set('config.changed.source'):
            # update system source configuration and check for upgrade
            cephfs_charm.install()
            cephfs_charm.upgrade_if_available([ceph_mds])
            reactive.clear_flag('config.changed.source')
        reactive.set_flag('cephfs.configured')
        reactive.set_flag('config.rendered')
        cephfs_charm.assess_status()
