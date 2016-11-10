#!/usr/bin/python3
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
import os
from charmhelpers.core.hookenv import action_get, action_fail, action_set
import xattr

__author__ = 'Chris Holcombe <chris.holcombe@canonical.com>'


def get_quota():
    max_files = action_get('max-files')
    max_bytes = action_get('max-bytes')
    directory = action_get('directory')

    if not os.path.exists(directory):
        action_fail("Directory must exist before setting quota")
    attr = "ceph.quota.{}"
    if max_files:
        attr = attr.format("max_files")
    elif max_bytes:
        attr = attr.format("max_bytes")

    try:
        quota_value = xattr.getxattr(directory, attr)
        action_set({'{} quota'.format(directory): quota_value})
    except IOError as err:
        action_fail(
            "Unable to get xattr on {}.  Error: {}".format(directory, err))


if __name__ == '__main__':
    get_quota()
