# Overview

[Ceph][ceph-upstream] is a unified, distributed storage system designed for
excellent performance, reliability, and scalability.

The ceph-fs charm deploys the metadata server daemon (MDS) for the Ceph
distributed file system (CephFS). It is used in conjunction with the
[ceph-mon][ceph-mon-charm] and the [ceph-osd][ceph-osd-charm] charms.

Highly available CephFS is achieved by deploying multiple MDS servers (i.e.
multiple ceph-fs units).

# Usage

## Configuration

This section covers common and/or important configuration options. See file
`config.yaml` for the full list of options, along with their descriptions and
default values. A YAML file (e.g. `ceph-osd.yaml`) is often used to store
configuration options. See the [Juju documentation][juju-docs-config-apps] for
details on configuring applications.

#### `source`

The `source` option states the software sources. A common value is an OpenStack
UCA release (e.g. 'cloud:xenial-queens' or 'cloud:bionic-ussuri'). See [Ceph
and the UCA][cloud-archive-ceph]. The underlying host's existing apt sources
will be used if this option is not specified (this behaviour can be explicitly
chosen by using the value of 'distro').

## Deployment

We are assuming a pre-existing Ceph cluster.

To deploy a single MDS node:

    juju deploy ceph-fs

Then add a relation to the ceph-mon application:

    juju add-relation ceph-fs:ceph-mds ceph-mon:mds

## Actions

This section lists Juju [actions][juju-docs-actions] supported by the charm.
Actions allow specific operations to be performed on a per-unit basis. To
display action descriptions run `juju actions ceph-fs`. If the charm is not
deployed then see file `actions.yaml`.

* `get-quota`
* `remove-quota`
* `set-quota`

# Bugs

Please report bugs on [Launchpad][lp-bugs-charm-ceph-fs].

For general charm questions refer to the OpenStack [Charm Guide][cg].

<!-- LINKS -->

[cg]: https://docs.openstack.org/charm-guide
[ceph-upstream]: https://ceph.io
[ceph-mon-charm]: https://jaas.ai/ceph-mon
[ceph-osd-charm]: https://jaas.ai/ceph-osd
[juju-docs-actions]: https://jaas.ai/docs/actions
[juju-docs-config-apps]: https://juju.is/docs/configuring-applications
[lp-bugs-charm-ceph-fs]: https://bugs.launchpad.net/charm-ceph-fs/+filebug
[cloud-archive-ceph]: https://wiki.ubuntu.com/OpenStack/CloudArchive#Ceph_and_the_UCA
