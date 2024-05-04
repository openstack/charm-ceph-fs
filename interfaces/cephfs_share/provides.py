from charms.reactive import scopes, when, set_flag, clear_flag
from charms.reactive.endpoints import Endpoint

from charmhelpers.core import hookenv

from typing import Iterable, Dict, Set

import json

class _Transaction:
    """Store transaction information between data mappings."""

    def __init__(self, added: Set, changed: Set, deleted: Set):
        self.added: Set = added
        self.changed: Set = changed
        self.deleted: Set = deleted

def _eval(relation) -> _Transaction:
    """Evaluate the difference between data in an integration changed databag.

    Args:
        relation: Relation with the written data.

    Returns:
        _Transaction:
            Transaction info containing the added, deleted, and changed
            keys from the relation databag.
    """
    # Retrieve the old data from the data key in the unit databag.
    old_data = json.loads(relation.to_publish_raw.get("cache", "{}"))
    # Retrieve the new data from the relation integration databag.
    new_data = {
        key: value for key, value in relation.received_app.items() if key != "cache"
    }
    # These are the keys that were added to the databag and triggered this event.
    added = new_data.keys() - old_data.keys()
    # These are the keys that were removed from the databag and triggered this event.
    deleted = old_data.keys() - new_data.keys()
    # These are the keys that were added or already existed in the databag, but had their values changed.
    changed = added.union(
        {key for key in old_data.keys() & new_data.keys() if old_data[key] != new_data[key]}
    )
    # Convert the new_data to a serializable format and save it for a next diff check.
    relation.to_publish_raw.update({
        "cache": json.dumps(new_data)
    })

    # Return the transaction with all possible changes.
    return _Transaction(added, changed, deleted)

class CephFSProvides(Endpoint):

    @when('endpoint.{endpoint_name}.changed')
    def changed(self):
        if hookenv.is_leader():
            for relation in self.relations:
                transaction = _eval(relation)
                if "name" in transaction.added:
                    set_flag(self.expand_name('{endpoint_name}.available'))

    def manage_flags(self):
        if not self.is_joined:
            clear_flag(
                self.expand_name('{endpoint_name}.available')
            )

    def set_share(self, share_info: Dict, auth_info: Dict) -> None:
        """Set info for mounting a CephFS share.

        Args:
            relation:
            share_info: Dictionary with the information required to mount the CephFS share.
                - fsid: ID of the Ceph cluster.
                - name: Name of the exported Ceph filesystem.
                - path: Exported path of the Ceph filesystem.
                - monitor_hosts: Address list of the available Ceph MON nodes.
            auth_info: Dictionary with the information required to authenticate against the Ceph cluster.
                - username: Name of the user authorized to access the Ceph filesystem.
                - key: Cephx key for the authorized user.

        Notes:
            Only the application leader unit can set the CephFS share data.
        """
        if hookenv.is_leader():
            share_info = json.dumps({
                    'fsid': share_info['fsid'],
                    'name': share_info['name'],
                    'path': share_info['path'],
                    'monitor_hosts': share_info['monitor_hosts']
                })
            auth_info = json.dumps({
                    'username': auth_info['username'],
                    'key': auth_info['key']
                })
            for relation in self.relations:
                relation.to_publish_app_raw.update({
                    "share_info": share_info,
                    "auth": f"plain:{auth_info}",
                })
