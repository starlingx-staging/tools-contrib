#!/bin/bash
. ./.bashrc
vuls configtest -config=/home/wrsroot/config.toml localhost
vuls scan -config=/home/wrsroot/config.toml localhost
vuls report -format-full-text >report_full_text_`date +"%Y%m%d"`.txt
vuls report -format-list >report_format_list_`date +"%Y%m%d"`.txt
