# StarlingX metrics

This project setups the infrastructure to enable the monitoring of StarlingX systems. This is achieved using [Prometheus](https://prometheus.io) for data gathering, the [Prometheu's node_exporter](https://github.com/prometheus/node_exporter) for monitoring and Grafana for data presentations.

## Installation

### Requirements

This project assumes that docker-compose is installed in your system. For more details on how to install docker-compose, [see here](https://docs.docker.com/compose/install/).

The following python packages are required: `pyyaml` and `paramiko`.

Also, it is expected that a set of StarlingX systems are configured and reachable by network.

### Setup the infrastructure

Three containers will be launch in this stage.

1. __nginx_: This is used to serve files to the StarlingX systems. In some deployments these systems doesn't have Internet access, so all required files are downloaded and then exposed through this web service.
2. _prometheus_: This is the monitoring system that will retrieve data from remote data exporters.
3. _grafana_: The dashboard to present the data. Grafana will connect to Prometheus to get the data.

Before starting the infrastructure you may want to configure Prometheus. In the `config/prometheus.yml` there is an example on how to configure prometheus.

The `setup-infra.sh` script downloads the `node_exporter` and execute `docker-compose` to launch the containers.

## Setup StarlingX systems.

The `deployer.py` script is in charge of execute commands in the remote StarlingX systems. The `config.yaml` file is used to provide configuration to this script, here the user name, password, local IP and remote IP address should be detailed.

To run this script just execute:

```
python3 deployer.py
```

## TODO
 - [ ] Configure a storage backend for Prometheus.
 - [ ] Find a way to tag data in the `node_exporter` using the `/etc/build.info` data.
 - [ ] Identify needed queries for anomaly detection.
 - [X] Create a basic docker compose file to launch prometheus and grafana.
 - [X] Create a script to download the node exporter and install it in the target system.
 - [X] Create a systemd file to configure the node exporter
 - [ ] Find a way to auto configure grafana.
