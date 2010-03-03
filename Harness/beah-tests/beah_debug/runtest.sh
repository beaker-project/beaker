#!/bin/bash

# Source the common test script helpers
. /usr/bin/rhts_environment.sh

for sysconf in /etc/sysconfig/beah-{srv,fakelc,{fwd,beaker}-backend}; do
echo 'OPTIONS="$OPTIONS -vvvv"' >> $sysconf
done

report_result $TEST PASS 0

