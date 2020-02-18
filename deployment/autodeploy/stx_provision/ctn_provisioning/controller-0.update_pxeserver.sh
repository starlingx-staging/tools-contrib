#!/bin/sh
set -ex

sudo sed -i 's/chage -d 0 sysadmin/#chage -d 0 sysadmin/g' \
	`grep "chage -d 0 sysadmin" /www/pages/feed/ -rl `

grep "chage -d 0 sysadmin" /www/pages/feed/ -rl
