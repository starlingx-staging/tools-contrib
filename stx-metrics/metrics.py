import subprocess
import argparse

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
    args = parser.parse_args()

    if args.boottime:
        print ("kernel space time = " + get_time("kernel"))
        print ("user space time = " + get_time("userspace"))

    if args.hd_footprint:
        total_hd,used_hd,avail_hd,per_hd = get_hd_footprint()
        print("total_hd = " +  total_hd)
        print("used_hd = " + used_hd)
        print("avail_hd = " + avail_hd)
        print("per_hd = " + per_hd)

    if args.memory_footprint:
        mem_total,mem_used = memory_footprint("Mem")
        print ("\nMemory\n")
        print ("    total = " + mem_total)
        print ("    used = " + mem_used)

        mem_total,mem_used = memory_footprint("Swap")
        print ("\nSwap memory\n")
        print ("    total = " + mem_total)
        print ("    used = " + mem_used)


if __name__ == "__main__":
    main()

