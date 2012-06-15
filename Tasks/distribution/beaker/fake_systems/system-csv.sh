#!/bin/bash
set -e

: ${TEST_SYSTEM_COUNT:=0}
: ${TEST_SYSTEM_COUNT_AUTOMATED:=0}
: ${TEST_SYSTEM_PREFIX:=test-}

# Put quotes around the header fields to work around bz802842
echo '"csv_type","fqdn","arch","type","lab_controller","vendor","model","location","status"'
seq $TEST_SYSTEM_COUNT | while read n ; do
    [ $n -lt $TEST_SYSTEM_COUNT_AUTOMATED ] && status=Automated || status=Manual
    echo "system,$TEST_SYSTEM_PREFIX$n.invalid,x86_64,Machine,$HOSTNAME,Fake,Fake,Non-existent,$status"
done
