#!/bin/bash
set -e

: ${TEST_SYSTEM_COUNT:=0}
: ${TEST_SYSTEM_PREFIX:=test-}

seq $TEST_SYSTEM_COUNT | while read n ; do
    echo "127.1.$(($n / 256)).$(($n % 256))  $TEST_SYSTEM_PREFIX$n.invalid"
done
