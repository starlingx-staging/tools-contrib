#!/usr/bin/expect -f

set timeout -1

set my_password [lindex $argv 0]

spawn ./test.sh

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
    "*(yes*no)?" {
        send "yes\r"
        expect "*assword:" {
            send "$my_password\n"
            expect eof
        }
    }
    "*assword:" {
        send -- "$my_password\r"
        expect eof
    }
    eof
}



