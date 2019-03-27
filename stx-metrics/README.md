# metrics tests

This project a short guide to inject metrics results in a [InfluxDB] database,
this is in order to be plotted by [Grafana] project and track different relevant
performance metrics of [StarlingX] project.

**NOTE:**
This basic script includes hard-code and this have to be just a **reference**
about how to inject information in a remote server and which configuration
has to be set in this server in order to receive the metrics values correctly.

This group of instructions was testd in Ubuntu 18.04.


**Insert data**

```
$ python3 insertdb.py
```

**Database query**

```
$ python3 querydb.py
```

### Configuration

#### Client

In client side will be executed the scripts of this project, however they
require the next configuration.

```
$ sudo apt-get install python-influxdb
```

#### Server

Install [InfluxDB] and [Grafana] and dependencies

```
$ sudo apt-get install influxdb-client
$ sudo apt-get install grafana
```

Start systemd service

```
$ sudo systemctl start influxdb
$ sudo systemctl start grafana
```

Start interactive mode

```
$ influx
```

Set the DB configuration inside [InfluxDB] client.
```
> create database starlingx
> show databases
> use starlingx
> insert release_19_01,test=vm_boottime value=0.64
> select * from release_19_01
name: release_19_01
time			test		value
----			----		-----
1553710826819450479	vm_boottime	0.64
```

[Grafana]: https://grafana.com/
[InfluxDB]: https://github.com/influxdata/influxdb
[StarlingX]: http://www.starlingx.io/
