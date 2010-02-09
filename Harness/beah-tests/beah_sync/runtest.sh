#!/bin/sh

# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.# The toplevel namespace within which the test lives.
#
# Author: Bill Peck

# Environment Variables
# $JOBID
# $DISTRO
# $ARCH
# $TEST
# $FAMILY
# $VARIANT
# $ARGS

# source the test script helpers
. /usr/bin/rhts-environment.sh

Client() {
    rhts-sync-set -s READY
    rhtsecho "Waiting for servers."
    rhts-sync-block -s READY $SERVERS
    rhtsecho "Servers are READY."
    rhts-sync-set -s DONE
    report_result $TEST Pass 0
}

Server() {
    rhts-sync-set -s READY
    rhtsecho "Waiting for clients."
    rhts-sync-block -s DONE $CLIENTS
    rhtsecho "Clients are DONE."
    rhts-sync-set -s DONE
    report_result $TEST Pass 0
}

rhtsecho() {
    echo "$@" | tee -a $OUTPUTFILE
}

# ---------- Start Test -------------
rhtsecho "***** Start of runtest.sh *****"

if [ -z "$SERVERS" -o -z "$CLIENTS" ]; then
    rhtsecho "Can not determine my Role! Client/Server Failed:"
    rhtsecho "If you are running this as a developer try setting" \
    rhtsecho "the environment variables CLIENTS and SERVERS" \
    report_result $TEST Warn
    exit 1
fi

if echo $CLIENTS | grep -q $HOSTNAME; then
    rhtsecho "Running beah-sync test as client"
    TEST="$TEST/client"
    Client
fi
if echo $SERVERS | grep -q $HOSTNAME; then
    rhtsecho "Running beah-sync test as server"
    TEST="$TEST/server"
    Server
fi
