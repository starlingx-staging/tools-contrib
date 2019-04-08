#!/bin/bash
cp ~/report_*.txt .
from="email_that_will_appear_as_sender"
to="comma_separated_list_of_recipients"
subject="VULS scan report full text `date +\"%Y%m%d\"`"
echo -e "subject: ${subject}\nfrom: $from\n" >head
cat head report_full_text_`date +"%Y%m%d"`.txt | sendmail $to
subject="VULS scan report format list `date +\"%Y%m%d\"`"
echo -e "subject: ${subject}\nfrom: $from\n" >head
cat head report_format_list_`date +"%Y%m%d"`.txt | sendmail $to
