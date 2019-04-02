#!/bin/sh

PNAME=$1

top -n 1 | grep $PNAME | awk '{print " pid:"$(NF-12)" cpu:"$(NF-4); }'

