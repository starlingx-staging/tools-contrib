#!/bin/bash

set -e

echo "Downloading packages"

pushd downloads
curl -L -# -o node_exporter-0.18.1.linux-amd64.tar.gz \
     https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz

tar -zxf node_exporter-0.18.1.linux-amd64.tar.gz
mv node_exporter-0.18.1.linux-amd64/node_exporter .
rm node_exporter-0.18.1.linux-amd64.tar.gz
rm -rf node_exporter-0.18.1.linux-amd64

popd

echo "Starting services"

sudo docker-compose -f docker-compose.yml build
sudo docker-compose -f docker-compose.yml start
