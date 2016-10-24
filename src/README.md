# CephFS Charm

# Overview

Ceph is a distributed storage and network file system designed to provide
excellent performance, reliability, and scalability.

This charm deploys a Ceph MDS cluster.

Usage
=====

Boot things up by using:

    juju deploy -n 3 --config ceph.yaml ceph-mon
    juju deploy -n 3 --config ceph.yaml ceph-osd
In my example deployments on EC2 the following ceph.yaml will work:
```
ceph-mon:
  source: cloud:trusty-mitaka
ceph-osd:
  osd-devices: /dev/xvdb
  ephemeral-unmount: "/mnt"
  source: cloud:trusty-mitaka
```
You can then deploy this charm by simply doing:

    juju deploy --config ceph.yaml ceph-fs
    juju add-relation ceph-fs ceph-mon

Once the ceph-mon and osd charms have bootstrapped the cluster, the ceph-mon
charm will notify the ceph-fs charm.

Contact Information
===================

## Ceph

- [Ceph website](http://ceph.com)
- [Ceph mailing lists](http://ceph.com/resources/mailing-list-irc/)
- [Ceph bug tracker](http://tracker.ceph.com/projects/ceph)
