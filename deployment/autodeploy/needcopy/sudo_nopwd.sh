#!/usr/bin/env bash


user=`whoami`
cat << EOF | sudo tee /etc/sudoers.d/${user}
${user} ALL = (root) NOPASSWD:ALL
EOF


