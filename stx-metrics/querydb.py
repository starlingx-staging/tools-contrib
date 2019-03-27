import random
import time

from influxdb import InfluxDBClient

# This section include all needed information for
# Influx database connection.
INFLUX_SERVER = 'localhost'
INFLUX_PORT = '8086'
INFLUX_PASS = 'root'
INFLUX_USER = 'root'

# Table information
table = "vm_metrics"

# Make query
client = InfluxDBClient(INFLUX_SERVER, INFLUX_PORT,
                            INFLUX_USER, INFLUX_PASS, 'starlingx')
query = "select value from %s;" % (table)
result = client.query(query)
print(result)
