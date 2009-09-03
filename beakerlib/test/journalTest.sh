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
# Author: Ales Zelinka <azelinka@redhat.com>

test_rlJournalStart(){
	local TID=${TESTID:-"debugging"}
	local JFILE="/tmp/beakerlib_journal.$TID"
	rm -f $JFILE
	assertTrue "journal started" "rlJournalStart"
	assertTrue "journal file created" "[ -f $JFILE ]"
	assertTrue "journal is well-formed XML" "xmllint $JFILE >/dev/null"
}

test_rlPrintJournal(){
	#add something to journal
	rlJournalStart
	rlPhaseStart FAIL
	rlAssert0 "failed" 1
	rlAssert0 "passed" 0
	rlPhaseEnd
	rlLog "loginek"
	assertTrue "rlJournalPrint dump is wellformed xml" "rlJournalPrint |xmllint -"
	assertTrue "rlPrintJournal dump still works" "rlPrintJournal | grep -v 'rlPrintJournal is obsoleted by rlJournalPrint' | xmllint -"
	assertTrue "rlPrintJournal emits obsolete warnings" "rlPrintJournal | grep 'rlPrintJournal is obsoleted by rlJournalPrint' -q"
}

test_rlCreateLogFromJournal(){
	#this fnc is used a lot in other function's tests
	#so here goes only some specific (regression?) tests

	#must not tracedump on an empty log message
	rlJournalStart
	#outside-of-phase log
  rlLog ""
	rlPhaseStart FAIL
	#inside-phase log
	rlLog ""
	assertFalse "no traceback during log creation" "rlJournalPrintText 2>&1 |grep Traceback"

    #no traceback on non-ascii characters (bz471257)
	rlJournalStart
	rlPhaseStart FAIL
    rlLog "ščřžýáíéーれっどはっと"
	assertFalse "no traceback on non-ascii chars (unicode support)" "rlJournalPrintText 2>&1 |grep Traceback"

  # no traceback on non-xml garbage
  rlJournalStart
  rlPhaseStart FAIL
  rlLog "`echo $'\x00'`"
  rlLog "`echo $'\x0c'`"
  rlLog "`echo $'\x1F'`"
	assertFalse "no traceback on non-xml characters" "rlJournalPrintText 2>&1 |grep Traceback"

  rlPhaseEnd
  rlJournalStart
}

test_rlPrintJournalText()
{
    rlJournalStart
    rlLog "`echo -e 'line1\nline2'`"
    rlJournalPrintText | grep -v "line2" | grep -q "LOG.*line1" && rlJournalPrintText | grep -v "line1" |grep -q "LOG.*line2"
    assertTrue "multiline logs tagged on each line" "[ $? -eq 0 ]"
}
