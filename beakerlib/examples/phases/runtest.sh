#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /examples/beakerlib/Sanity/phases
#   Description: Testing BeakerLib phases
#   Author: Petr Splichal <psplicha@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2009 Red Hat, Inc. All rights reserved.
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

# Include rhts environment
. /usr/bin/rhts-environment.sh
. /usr/beaker/beakerlib/beakerlib.sh

PACKAGE="beakerlib"

rlJournalStart

    # Failing phases
    rlPhaseStartSetup "Bad setup"
        rlRun "ls -l nothing"
    rlPhaseEnd

    rlPhaseStartTest "Bad testing"
        rlRun "ls -l nothing"
    rlPhaseEnd

    rlPhaseStartCleanup "Bad cleanup"
        rlRun "ls -l nothing"
    rlPhaseEnd

    # Passing phases
    rlPhaseStartSetup "Good setup"
        rlRun "ls -l"
    rlPhaseEnd

    rlPhaseStartTest "Good testing"
        rlRun "ls -l"
    rlPhaseEnd

    rlPhaseStartCleanup "Good cleanup"
        rlRun "ls -l"
    rlPhaseEnd

rlJournalPrintText
rlJournalEnd
