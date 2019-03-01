# CephFS Charm

This charm exists to provide an example integration of CephFS, for the purpose
of test and reference.  It is not intended for production use at this time.

# Overview

Ceph is a distributed storage and network file system designed to provide
excellent performance, reliability, and scalability.

This charm deploys a Ceph MDS cluster.

Usage
=====

Boot things up by using:

    juju deploy -n 3 ceph-mon
    juju deploy -n 3 ceph-osd

You can then deploy this charm by simply doing:

    juju deploy ceph-fs
    juju add-relation ceph-fs ceph-mon

Once the ceph-mon and osd charms have bootstrapped the cluster, the ceph-mon
charm will notify the ceph-fs charm.

Contact Information
===================

## Ceph

- [Ceph website](http://ceph.com)
- [Ceph mailing lists](http://ceph.com/resources/mailing-list-irc/)
- [Ceph bug tracker](http://tracker.ceph.com/projects/ceph)
