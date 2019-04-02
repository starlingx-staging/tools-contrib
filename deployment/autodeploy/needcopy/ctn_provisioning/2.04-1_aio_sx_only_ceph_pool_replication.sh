#!/bin/sh

ceph osd pool ls | xargs -i ceph osd pool set {} size 1

