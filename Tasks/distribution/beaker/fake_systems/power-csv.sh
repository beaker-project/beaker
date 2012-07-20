#!/bin/bash
set -e

: ${TEST_SYSTEM_COUNT:=0}
: ${TEST_SYSTEM_PREFIX:=test-}

# Put quotes around the header fields to work around bz802842
echo '"csv_type","fqdn","power_address","power_type","power_id"'
seq $TEST_SYSTEM_COUNT | while read n ; do
    # This distribution of the different dummy power types is completely
    # unscientific and made-up. We don't want *too* many slow ones, otherwise
    # the load tests will just cause an exploding backlog.
    power_type=
    [ $(($n % 10)) -ge 9 ] && : ${power_type:=dummy_flakey}
    [ $(($n % 10)) -ge 8 ] && : ${power_type:=dummy_slow}
    [ $(($n % 10)) -ge 5 ] && : ${power_type:=dummy_medium}
    : ${power_type:=dummy_fast}
    echo "power,$TEST_SYSTEM_PREFIX$n.invalid,localhost,$power_type,$TEST_SYSTEM_PREFIX$n.invalid"
done
