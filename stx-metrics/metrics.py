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


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--boottime',\
        help='Print kernel/userspace boot time',\
        action='store_true')
    args = parser.parse_args()

    if args.boottime:
        print ("kernel space time = " + get_time("kernel"))
        print ("user space time = " + get_time("userspace"))

if __name__ == "__main__":
    main()

