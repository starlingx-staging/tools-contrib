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
test_name = "vm_boottime"
test_units = "ms"

# Data to be inserted
current_date = time.strftime("%c")
value = round(random.uniform(0.1, 10),2)
json_file = [
    {
        "measurement": table,
        "time": current_date,
        "fields": {
	    "test" : test_name,
	    "unit": test_units,
            "value": value
        }
    }
]

client = InfluxDBClient(INFLUX_SERVER, INFLUX_PORT,
                            INFLUX_USER, INFLUX_PASS, 'starlingx')
if client.write_points(json_file):
    print("Data inserted successfully")
else:
    print("Error during data insertion")

query = "select value from %s;" % (table)
result = client.query(query)
print("%s contains:" % table)
print(result)
