#!/usr/bin/env python

__author__      = "Mario Carrillo"

import random
import time
import argparse

from influxdb import InfluxDBClient

INFLUX_SERVER = ""
INFLUX_PORT = ""
INFLUX_PASS = ""
INFLUX_USER = ""

def send_data(json_file):

    client = InfluxDBClient(INFLUX_SERVER, INFLUX_PORT,
                                INFLUX_USER, INFLUX_PASS, 'starlingx')
    if client.write_points(json_file):
        print("Data inserted successfully")
    else:
        print("Error during data insertion")
    return client

def check_data(client,table):

    query = "select value from %s;" % (table)
    result = client.query(query)
    print("%s contains:" % table)
    print(result)

def main():

    global INFLUX_SERVER
    global INFLUX_PORT
    global INFLUX_PASS
    global INFLUX_USER

    parser = argparse.ArgumentParser()
    parser.add_argument('--server',\
        help='addres of the influxdb server')
    parser.add_argument('--port',\
        help='port of the influxdb server')
    parser.add_argument('--user',\
        help='user of the influxdb server')
    parser.add_argument('--password',\
        help='password of the influxdb server')

    args = parser.parse_args()

    if args.server:
        INFLUX_SERVER = args.server
    if args.port:
        INFLUX_PORT = args.port
    if args.password:
        INFLUX_PASS = args.password
    if args.user:
        INFLUX_USER = args.password

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

    if INFLUX_SERVER and INFLUX_PORT and INFLUX_PASS and INFLUX_USER:
        client = send_data(json_file)
        check_data(client,table)

        time.sleep(10)
        current_date = time.strftime("%c")
        test_name = "vm_boottime_2"
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

        client = send_data(json_file)
        check_data(client,table)

if __name__ == '__main__':
    main()

