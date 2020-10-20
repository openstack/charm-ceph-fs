# Overview

[Ceph][ceph-upstream] is a unified, distributed storage system designed for
excellent performance, reliability, and scalability.

The ceph-fs charm deploys the metadata server daemon (MDS) for the Ceph
distributed file system (CephFS). The deployment is done within the context of
an existing Ceph cluster.

# Usage

## Configuration

This section covers common and/or important configuration options. See file
`config.yaml` for the full list of options, along with their descriptions and
default values. A YAML file (e.g. `ceph-osd.yaml`) is often used to store
configuration options. See the [Juju documentation][juju-docs-config-apps] for
details on configuring applications.

#### `pool-type`

The `pool-type` option dictates the storage pool type. See section 'Ceph pool
type' for more information.

#### `source`

The `source` option states the software sources. A common value is an OpenStack
UCA release (e.g. 'cloud:xenial-queens' or 'cloud:bionic-ussuri'). See [Ceph
and the UCA][cloud-archive-ceph]. The underlying host's existing apt sources
will be used if this option is not specified (this behaviour can be explicitly
chosen by using the value of 'distro').

## Ceph pool type

Ceph storage pools can be configured to ensure data resiliency either through
replication or by erasure coding. This charm supports both types via the
`pool-type` configuration option, which can take on the values of 'replicated'
and 'erasure-coded'. The default value is 'replicated'.

For this charm, the pool type will be associated with CephFS volumes.

> **Note**: Erasure-coded pools are supported starting with Ceph Luminous.

### Replicated pools

Replicated pools use a simple replication strategy in which each written object
is copied, in full, to multiple OSDs within the cluster.

The `ceph-osd-replication-count` option sets the replica count for any object
stored within the 'ceph-fs-data' cephfs pool. Increasing this value increases
data resilience at the cost of consuming more real storage in the Ceph cluster.
The default value is '3'.

> **Important**: The `ceph-osd-replication-count` option must be set prior to
  adding the relation to the ceph-mon application. Otherwise, the pool's
  configuration will need to be set by interfacing with the cluster directly.

### Erasure coded pools

Erasure coded pools use a technique that allows for the same resiliency as
replicated pools, yet reduces the amount of space required. Written data is
split into data chunks and error correction chunks, which are both distributed
throughout the cluster.

> **Note**: Erasure coded pools require more memory and CPU cycles than
  replicated pools do.

When using erasure coded pools for CephFS file systems two pools will be
created: a replicated pool (for storing MDS metadata) and an erasure coded pool
(for storing the data written into a CephFS volume). The
`ceph-osd-replication-count` configuration option only applies to the metadata
(replicated) pool.

Erasure coded pools can be configured via options whose names begin with the
`ec-` prefix.

> **Important**: It is strongly recommended to tailor the `ec-profile-k` and
  `ec-profile-m` options to the needs of the given environment. These latter
  options have default values of '1' and '2' respectively, which result in the
  same space requirements as those of a replicated pool.

See [Ceph Erasure Coding][cdg-ceph-erasure-coding] in the [OpenStack Charms
Deployment Guide][cdg] for more information.

## Ceph BlueStore compression

This charm supports [BlueStore inline compression][ceph-bluestore-compression]
for its associated Ceph storage pool(s). The feature is enabled by assigning a
compression mode via the `bluestore-compression-mode` configuration option. The
default behaviour is to disable compression.

The efficiency of compression depends heavily on what type of data is stored
in the pool and the charm provides a set of configuration options to fine tune
the compression behaviour.

> **Note**: BlueStore compression is supported starting with Ceph Mimic.

## Deployment

To deploy a single MDS node within an existing Ceph cluster:

    juju deploy ceph-fs
    juju add-relation ceph-fs:ceph-mds ceph-mon:mds

## High availability

Highly available CephFS is achieved by deploying multiple MDS servers (i.e.
multiple ceph-fs units).

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
[cdg]: https://docs.openstack.org/project-deploy-guide/charm-deployment-guide
[ceph-upstream]: https://ceph.io
[juju-docs-actions]: https://jaas.ai/docs/actions
[juju-docs-config-apps]: https://juju.is/docs/configuring-applications
[lp-bugs-charm-ceph-fs]: https://bugs.launchpad.net/charm-ceph-fs/+filebug
[cloud-archive-ceph]: https://wiki.ubuntu.com/OpenStack/CloudArchive#Ceph_and_the_UCA
[cdg-ceph-erasure-coding]: https://docs.openstack.org/project-deploy-guide/charm-deployment-guide/latest/app-erasure-coding.html
[ceph-bluestore-compression]: https://docs.ceph.com/en/latest/rados/configuration/bluestore-config-ref/#inline-compression
