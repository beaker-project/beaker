#!/bin/bash

# Copyright (c) 2012 Red Hat, Inc. All rights reserved. This copyrighted material 
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
# Author: Dan Callaghan <dcallagh@redhat.com>

. /usr/share/beakerlib/beakerlib.sh

function LabController()
{
 rlJournalStart
   rlPhaseStartSetup
    rlRun "yum install -y curl python-daemon python-lxml python-gevent"
    rlRun "cp dummy_* /etc/beaker/power-scripts/" 0 "Installing dummy power scripts"
    rlRun "./beah_dummy.py" 0 "Starting beah_dummy.py daemon"
    rlLog "Adding fake entries to /etc/hosts"
    ./hosts.sh >>/etc/hosts
    rlLog "Generating fake system CSV files"
    ./system-csv.sh >systems.csv
    ./power-csv.sh >power.csv
    rlRun "curl -f -s -o /dev/null -c cookie -d user_name=admin -d password=testing -d login=1 http://$SERVER/bkr/login" 0 "Logging in to Beaker server"
    rlRun "curl -f -s -o /dev/null -b cookie --form csv_file=@systems.csv http://$SERVER/bkr/csv/action_import" 0 "Uploading systems CSV"
    rlRun "curl -f -s -o /dev/null -b cookie --form csv_file=@power.csv http://$SERVER/bkr/csv/action_import" 0 "Uploading power CSV"
   rlPhaseEnd
 rlJournalEnd
}

function Inventory()
{
 rlJournalStart
   rlPhaseStartSetup
    rlRun "curl -f -s -o /dev/null -c cookie -d user_name=admin -d password=testing -d login=1 http://localhost/bkr/login" 0 "Logging in to Beaker server"
    for powertype in dummy_* ; do
        rlRun "curl -f -s -o /dev/null -b cookie -d name=$powertype -d id= http://localhost/bkr/powertypes/save" 0 "Adding dummy power type $powertype in Beaker"
    done
   rlPhaseEnd
 rlJournalEnd
}

if grep -q $HOSTNAME <<<"$CLIENTS" ; then
    rlLog "Running as Lab Controller using Inventory: ${SERVERS}"
    TEST="$TEST/lab_controller"
    SERVER=$(echo $SERVERS | awk '{print $1}')
    LabController
    exit 0
fi

if grep -q $HOSTNAME <<<"$SERVERS" ; then
    rlLog "Running as Inventory using Lab Controllers: ${CLIENTS}"
    TEST="$TEST/inventory"
    Inventory
    exit 0
fi

if [ -z "$SERVERS" -o -z "$CLIENTS" ]; then
    rlLog "Inventory=${SERVERS} LabController=${CLIENTS} Assuming Single Host Mode."
    CLIENTS=$STANDALONE
    SERVERS=$STANDALONE
    SERVER=$(echo $SERVERS | awk '{print $1}')
    TEST="$TEST/lab_controller" LabController
    TEST="$TEST/inventory" Inventory
    exit 0
fi

rlDie "not reached"
