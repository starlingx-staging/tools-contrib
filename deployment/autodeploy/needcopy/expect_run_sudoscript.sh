#!/usr/bin/expect -f

set timeout -1

set my_password [lindex $argv 0]
set ip [lindex $argv 1]
set script [lindex $argv 2]

spawn ssh -t $ip sudo ./$script
expect {
    "*(yes*no)?" {
    	send "yes\r"
	expect "*assword:" { send "$my_password\n"}
    }
    "*assword:" {
    	send -- "$my_password\r"
    }
}
expect {
    "*assword:" {
        send "$my_password\r"
        expect eof
    }
    eof
}
