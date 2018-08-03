#!/bin/bash

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# See: https://beaker-project.org/docs/admin-guide/watchdog-script.html
# This watchdog script has some magic behaviour for use in Beaker's test suite.

system=$1
recipeid=$2
taskid=$3

case $system in
watchdog.script.please.crash)
    echo "watchdog script exiting non-zero as requested"
    exit 1
    ;;
watchdog.script.please.extend.600)
    echo 600
    ;;
*)
    echo "watchdog script exiting non-zero by default"
    exit 1
    ;;
esac
