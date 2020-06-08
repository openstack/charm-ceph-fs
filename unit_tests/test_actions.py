import sys

sys.path.append('src/actions')
import unittest
from unittest.mock import patch, call, Mock

__author__ = 'Chris Holcombe <chris.holcombe@canonical.com>'

sys.modules['action_set'] = Mock()
sys.modules['action_get'] = Mock()
sys.modules['action_fail'] = Mock()
sys.modules['xattr'] = Mock()
from get_quota import get_quota
from remove_quota import remove_quota
from set_quota import set_quota


def action_get_side_effect(*args):
    if args[0] == 'max-files':
        return 1024
    elif args[0] == 'max-bytes':
        return 1024
    elif args[0] == 'directory':
        return 'foo'


class CephActionsTestCase(unittest.TestCase):
    @patch('get_quota.action_fail')
    @patch('get_quota.action_set')
    @patch('get_quota.action_get')
    @patch('get_quota.os')
    @patch('get_quota.xattr')
    def test_get_quota(self, xattr, os, action_get, action_set, action_fail):
        action_get.side_effect = action_get_side_effect
        os.path.exists.return_value = True
        xattr.getxattr.return_value = "1024"
        get_quota()
        action_get.assert_has_calls(
            [call('max-files'),
             call('max-bytes'),
             call('directory')])
        action_fail.assert_not_called()
        xattr.getxattr.assert_called_with('foo',
                                          'ceph.quota.max_files')
        action_set.assert_called_with({'foo quota': "1024"})

    @patch('set_quota.action_fail')
    @patch('set_quota.action_get')
    @patch('set_quota.os')
    @patch('set_quota.xattr')
    def test_set_quota(self, xattr, os, action_get, action_fail):
        action_get.side_effect = action_get_side_effect
        os.path.exists.return_value = True
        set_quota()
        xattr.setxattr.assert_called_with('foo',
                                          'ceph.quota.max_files',
                                          '1024')
        action_get.assert_has_calls(
            [call('max-files'),
             call('max-bytes'),
             call('directory')])
        action_fail.assert_not_called()

    @patch('remove_quota.action_fail')
    @patch('remove_quota.action_get')
    @patch('remove_quota.os')
    @patch('remove_quota.xattr')
    def test_remove_quota(self, xattr, os, action_get, action_fail):
        action_get.side_effect = action_get_side_effect
        os.path.exists.return_value = True
        remove_quota()
        xattr.setxattr.assert_called_with('foo',
                                          'ceph.quota.max_files',
                                          '0')
        action_get.assert_has_calls(
            [call('max-files'),
             call('max-bytes'),
             call('directory')])
        action_fail.assert_not_called()
