#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__      = "Victor Rodriguez"

import subprocess
import argparse
from time import sleep
import os.path
import json

data = {}

def get_time(space):
    proc = subprocess.Popen(['systemd-analyze','time'],stdout=subprocess.PIPE)
    while True:
      line = proc.stdout.readline()
      if space in line:
        line_array = (line.rstrip().split())
        count = 0
        for element in line_array:
            if space in element:
                break
            count = count + 1
        return line_array[count -1]
        break
      else:
        break

def get_hd_footprint():
    proc = subprocess.Popen(['df','-h'],stdout=subprocess.PIPE)
    while True:
        line = proc.stdout.readline()
        if line != '':
            if "/" in line:
              line_array = (line.rstrip().split())
              for element in line_array:
                if "/" == line_array[len(line_array)-1]:
                    sda = (line)
                    break
        else:
            break
    if sda:
        total_hd = (sda.split()[1])
        used_hd = (sda.split()[2])
        avail_hd = (sda.split()[3])
        per_hd = (sda.split()[4])
        return total_hd,used_hd,avail_hd,per_hd

def memory_footprint(memory_kind):
    proc = subprocess.Popen(['free','-h'],stdout=subprocess.PIPE)
    while True:
        line = proc.stdout.readline()
        if line != '':
            if memory_kind in line:
              line_array = (line.rstrip().split())
              mem_total = line_array[1]
              mem_used = line_array[2]
              break
        else:
            break
    return mem_total,mem_used

def get_cpu_utilization(seconds):
    delay = 5
    loop = 0
    loops = seconds / delay
    last_idle = last_total = 0
    total_util = 0.0
    while True:
        with open('/proc/stat') as f:
            fields = [float(column) for column in f.readline().strip().split()[1:]]
        idle, total = fields[3], sum(fields)
        idle_delta, total_delta = idle - last_idle, total - last_total
        last_idle, last_total = idle, total
        utilisation = 100.0 * (1.0 - idle_delta / total_delta)
        print('%5.1f%%' % utilisation)
        total_util += utilisation
        sleep(delay)
        loop = loop +1
        if loop >= loops:
            break
    if loops:
        average = (total_util/loops)
    return average

def print_hd_footprint():
    total_hd,used_hd,avail_hd,per_hd = get_hd_footprint()
    print("\n===================================")
    print("Hard Drive Footprint")
    print("===================================\n")
    print("total_hd = " +  total_hd)
    print("used_hd = " + used_hd)
    print("avail_hd = " + avail_hd)
    print("per_hd = " + per_hd)

    data['hd_footprint'] = []
    data['hd_footprint'].append({
        'total_hd': total_hd,
        'used_hd': used_hd,
        'avail_hd': avail_hd,
        'per_hd':per_hd
    })

def print_boottime():

    kernel_time = get_time("kernel")
    userspace_time = get_time("userspace")

    print("\n===================================")
    print("System Boottime")
    print("===================================\n")
    print ("kernel space boot time = " + kernel_time)
    print ("user space boot time = " + userspace_time)

    data['boot_time'] = []
    data['boot_time'].append({
        'kernel_space': kernel_time,
        'user_space': userspace_time
    })

def print_memory_footprint():
    mem_total,mem_used = memory_footprint("Mem")
    print("\n===================================")
    print(" Virtual Memory Footprint")
    print("===================================\n")
    print ("\nMemory\n")
    print ("    total = " + mem_total)
    print ("    used = " + mem_used)

    data['memory'] = []
    data['memory'].append({
        'memory_total': mem_total,
        'memory_used': mem_used
    })

    mem_total,mem_used = memory_footprint("Swap")
    print ("\nSwap memory\n")
    print ("    total = " + mem_total)
    print ("    used = " + mem_used)

    data['swap_memory'] = []
    data['swap_memory'].append({
        'memory_total': mem_total,
        'memory_used': mem_used
    })

def print_cpu_utilization(time):
    print("\n===================================")
    print(" CPU utilization")
    print("===================================\n")
    average = get_cpu_utilization(int(time))
    print ("Average CPU utilization = %5.1f%%" % average)

    data['cpu'] = []
    data['cpu'].append({
        'cpu utilization': average
    })

def print_host_data():
    print("\n===================================")
    print(" HOST INFO")
    print("===================================\n")
    filename = '/etc/lsb-release'
    if os.path.isfile(filename):
        FILE = open(filename,"r")
        print (FILE.read())

def generate_json(data):

    with open('data.json', 'w') as outfile:
        json.dump(data, outfile)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--boottime',\
        help='Print kernel/userspace boot time',\
        action='store_true')
    parser.add_argument('--hd_footprint',\
        help='Print HD footprint',\
        action='store_true')
    parser.add_argument('--memory_footprint',\
        help='Print virtual memory footprint',\
        action='store_true')
    parser.add_argument('--cpu_utilization',\
        help='Print cpu utilization over X seconds')
    args = parser.parse_args()

    print_host_data()
    time = 120

    if args.boottime:
        print_boottime()

    elif args.hd_footprint:
        print_hd_footprint()

    elif args.memory_footprint:
        print_memory_footprint()

    elif args.cpu_utilization:
        if args.cpu_utilization <= 0:
            time = 120
        else:
            time = args.cpu_utilization
        print_cpu_utilization(time)

    else:
        print_boottime()
        print_hd_footprint()
        print_memory_footprint()
        print_cpu_utilization(time)

    generate_json(data)

if __name__ == "__main__":
    main()

