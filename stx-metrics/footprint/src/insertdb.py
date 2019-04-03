#!/usr/bin/env python

__author__      = "Mario Carrillo/Victor Rodriguez"

import random
import time
import argparse
import json
import os
import logging

from influxdb import InfluxDBClient

INFLUX_SERVER = ""
INFLUX_PORT = ""
INFLUX_PASS = ""
INFLUX_USER = ""

def send_data(json_file,client):
    if client:
        if client.write_points(json_file):
            logging.info("Data inserted successfully")
            return True
        else:
            logging.error("Error during data insertion")
    else:
        logging.warning("Error the server is not configured yet: server.conf")
        return False

def check_data(client,table):

    query = "select value from %s;" % (table)
    result = client.query(query)
    print("%s contains:" % table)
    print(result)

def check_db_status(db_name):
    try:
        dbclient = InfluxDBClient(INFLUX_SERVER,\
                INFLUX_PORT,\
                INFLUX_USER,\
                INFLUX_PASS)
        dblist = dbclient.get_list_database()
        db_found = False
        for db in dblist:
            if db['name'] == db_name:
                db_found = True
        if not(db_found):
            logging.info('Database <%s> not found, trying to create it', db_name)
            dbclient.create_database(db_name)
        return True
    except Exception as e:
        logging.error('Error querying open-nti database: %s', e)
        return False


def get_server_data():

    global INFLUX_SERVER
    global INFLUX_PORT
    global INFLUX_PASS
    global INFLUX_USER

    config_file = "server.conf"
    client = None

    if os.path.isfile(config_file):
        FILE = open(config_file, "r")
        for line in FILE:
            if "#" in line:
                pass
            if "INFLUX_SERVER" in line:
                INFLUX_SERVER = line.split("=")[1].strip()
            if "INFLUX_PORT" in line:
                INFLUX_PORT = line.split("=")[1].strip()
            if "INFLUX_PASS" in line:
                INFLUX_PASS = line.split("=")[1].strip()
            if "INFLUX_USER" in line:
                INFLUX_USER = line.split("=")[1].strip()
            if "DB_NAME" in line:
                DB_NAME = line.split("=")[1].strip()
        if INFLUX_SERVER and INFLUX_PORT and INFLUX_PASS and INFLUX_USER:
            if check_db_status(DB_NAME):
                client = InfluxDBClient(INFLUX_SERVER, INFLUX_PORT,
                                            INFLUX_USER, INFLUX_PASS,DB_NAME)
    else:
        logging.error("Error server.conf missing")

    return client

def main():
    client = get_server_data()
    print(INFLUX_SERVER)
    print(INFLUX_PORT)
    print(INFLUX_PASS)
    print(INFLUX_USER)

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

    send_data(json_file,client)

if __name__ == '__main__':
    main()
