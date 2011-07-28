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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Bill Peck <bpeck@redhat.com>

# source the test script helpers
. /usr/bin/rhts-environment.sh

# Assume the test will fail.
result=FAIL

# Helper functions
# control where to log debug messages to:
# devnull = 1 : log to /dev/null
# devnull = 0 : log to file specified in ${DEBUGLOG}
devnull=0

# Create debug log
DEBUGLOG=`mktemp -p /mnt/testarea -t DeBug.XXXXXX`

# locking to avoid races
lck=$OUTPUTDIR/$(basename $0).lck

# Log a message to the ${DEBUGLOG} or to /dev/null
function DeBug ()
{
    local msg="$1"
    local timestamp=$(date '+%F %T')
    if [ "$devnull" = "0" ];then
	lockfile -r 1 $lck
	if [ "$?" = "0" ];then
	    echo -n "${timestamp}: " >>$DEBUGLOG 2>&1
	    echo "${msg}" >>$DEBUGLOG 2>&1
	    rm -f $lck >/dev/null 2>&1
	fi
    else
	echo "${msg}" >/dev/null 2>&1
    fi
}

function SubmitLog ()
{
    LOG=$1
    rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $LOG
}

function result_fail()
{
    echo "***** End of runtest.sh *****" | tee -a $OUTPUTFILE
    report_result $TEST FAIL 1
    SubmitLog $DEBUGLOG
    CleanUp
    exit 0
}

function result_pass ()
{
    echo "***** End of runtest.sh *****" | tee -a $OUTPUTFILE
    report_result $TEST PASS 0
    CleanUp
    exit 0
}

function CleanUp ()
{
    echo "no clean up method yet"
}

#Function below will report if a prev command failed
function estatus_fail()
{
    if [ "$?" -ne "0" ];then
	DeBug "$1 Failed"
	echo "***** "$1" Failed: *****" | tee -a $OUTPUTFILE
        rhts-sync-set -s ABORT
	result_fail
    fi
}

function Inventory()
{
    rhts-sync-set -s SERVERREADY
    rhts-sync-block -s DONE -s ABORT $CLIENTS
    result_pass 
}

function LabController()
{
    # Add some distros
    # NFS format HOSTNAME:DISTRONAME:NFSPATH
    if [ -z "$NFSDISTROS" ]; then
        echo "Missing NFS Distros to test with" | tee -a $OUTPUTFILE
        report_result $TEST Warn
        exit 1
    fi
    ln -s /net /var/www/html/net
    for distro in $NFSDISTROS; do
        NFSSERVER=$(echo $distro| awk -F: '{print $1}')
        DISTRONAME=$(echo $distro| awk -F: '{print $2}')
        NFSPATH=$(echo $distro| awk -F: '{print $3}')
        NFSDIR=$(dirname $NFSPATH)
        result="FAIL"
        echo cobbler import --path=/net/${NFSSERVER}${NFSPATH} \
                       --name=${DISTRONAME} \
                       --available-as=nfs://${NFSSERVER}:${NFSPATH}
        cobbler import --path=/net/${NFSSERVER}${NFSPATH} \
                       --name=${DISTRONAME} \
                       --available-as=nfs://${NFSSERVER}:${NFSPATH}
        score=$?
        if [ "$score" -eq "0" ]; then
            result="PASS"
        fi
        report_result $TEST/ADD_DISTRO/${DISTRONAME} $result $score
    done
    # Import Rawhide
    if [ -n "$RAWHIDE_NFS" ]; then
        NFSSERVER=$(echo $RAWHIDE_NFS| awk -F: '{print $1}')
        NFSDIR=$(echo $RAWHIDE_NFS| awk -F: '{print $2}')
        for distro in $(find /net/${NFSSERVER}${NFSDIR} -maxdepth 1 -name rawhide\* -type d); do 
            DISTRO=$(basename $distro)
            DISTRONAME=Fedora-$(basename $distro)
            result="FAIL"
            echo cobbler import \
                           --path=/net/${NFSSERVER}${NFSDIR}/${DISTRO} \
                           --name=${DISTRONAME} \
                           --available-as=nfs://${NFSSERVER}:${NFSDIR}/${DISTRO}
            cobbler import --path=/net/${NFSSERVER}${NFSDIR}/${DISTRO} \
                           --name=${DISTRONAME} \
                           --available-as=nfs://${NFSSERVER}:${NFSDIR}/${DISTRO}
            score=$?
            if [ "$score" -eq "0" ]; then
                result="PASS"
            fi
            report_result $TEST/ADD_DISTRO/${DISTRONAME} $result $score
        done
    fi
    cobbler distro report
    /var/lib/cobbler/triggers/sync/post/osversion.trigger | tee -a $OUTPUTFILE
    estatus_fail "**** Failed to run osversion.trigger ****"
    rhts-sync-set -s DONE
    result_pass 
}

if $(echo $CLIENTS | grep -q $HOSTNAME); then
    echo "Running test as Lab Controller" | tee -a $OUTPUTFILE
    TEST="$TEST/lab_controller"
    SERVER=$(echo $SERVERS | awk '{print $1}')
    SERVER_URL="https://testuser:testpassword\@$SERVER/bkr/"
    LabController
fi

if $(echo $SERVERS | grep -q $HOSTNAME); then
    echo "Running test as Inventory" | tee -a $OUTPUTFILE
    TEST="$TEST/inventory"
    Inventory
fi

if $(echo $STANDALONE | grep -q $HOSTNAME); then
    echo "Running test as both Lab Controller and Scheduler" | tee -a $OUTPUTFILE
    CLIENTS=$STANDALONE
    SERVERS=$STANDALONE
    SERVER=$(echo $SERVERS | awk '{print $1}')
    SERVER_URL="https://testuser:testpassword\@$SERVER/bkr/"
    TEST="$TEST/lab_controller" LabController &
    sleep 120
    TEST="$TEST/inventory" Inventory
fi

