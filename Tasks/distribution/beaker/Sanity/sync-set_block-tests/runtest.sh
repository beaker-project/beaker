#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /distribution/beaker/Sanity/sync-set_block-tests
#   Description: Verifies that the rhts-sync-[set|block] tests work correctly
#   Author: Bill Peck <bpeck@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1

PACKAGE="beaker"

function ClientOne()
{
 rlJournalStart
    rlPhaseStartSetup
        rlRun "rhts-sync-set -s READY"
        rlRun "rhts-sync-block -s READY $CLIENTTWO $SERVERS"
    rlPhaseEnd
    rlPhaseStartTest
        # Block on ClientTwo which is blocking on us.  we will timeout
        # first and exit with a non-zero return code.
        rlRun "rhts-sync-block --timeout 120 -s READY2 $CLIENTTWO" 1
        # Set our state to READY and ClientTwo will now set its state to READY
        rlRun "rhts-sync-set -s READY2"
        # This time we will return with a zero return code.
        rlRun "rhts-sync-block --timeout 120 -s READY2 $CLIENTTWO" 0
        # Sleep for 2 minutes so that the server will test the --any option
        rlRun "sleep 120"
        rlRun "rhts-sync-set -s DONE"
    rlPhaseEnd
 rlJournalPrintText
 rlJournalEnd
}

function ClientTwo()
{
 rlJournalStart
    rlPhaseStartSetup
        rlRun "rhts-sync-set -s READY"
        rlRun "rhts-sync-block -s READY $CLIENTONE $SERVERS"
    rlPhaseEnd
    rlPhaseStartTest
        rlRun "rhts-sync-block --timeout 240 -s READY2 $CLIENTONE" 0
        rlRun "rhts-sync-set -s READY2"
        rlRun "rhts-sync-set -s DONE"
    rlPhaseEnd
 rlJournalPrintText
 rlJournalEnd
}

function Server()
{
 rlJournalStart
    rlPhaseStartSetup
        rlRun "rhts-sync-set -s READY"
        rlRun "rhts-sync-block -s READY $CLIENTONE $CLIENTTWO"
    rlPhaseEnd

    rlPhaseStartTest
        rlRun "rhts-sync-block --any -s DONE $CLIENTONE $CLIENTTWO"
        rlRun "rhts-sync-block -s DONE $CLIENTONE $CLIENTTWO"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "rhts-sync-set -s DONE"
    rlPhaseEnd
 rlJournalPrintText
 rlJournalEnd
}

if $(echo $CLIENTONE | grep -q $HOSTNAME); then
    rlLog "Running as ClientOne: ${ClIENTONE}"
    TEST="$TEST/ClientOne"
    ClientOne
fi
if $(echo $CLIENTTWO | grep -q $HOSTNAME); then
    rlLog "Running as ClientTwo: ${ClIENTTWO}"
    TEST="$TEST/ClientTwo"
    ClientTwo
fi
if $(echo $SERVERS | grep -q $HOSTNAME); then
    rlLog "Running as Server: ${SERVERS}"
    TEST="$TEST/Server"
    Server
fi
