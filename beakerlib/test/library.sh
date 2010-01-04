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

#verify that commands adds exactly one test to journal
#(either pass or fail, depending on what's expected)
__one_fail_one_pass(){
	local CMD=$1
	local RESULT=$2
	if [ "x$RESULT" == "xPASS" ] ; then
		rm $BEAKERLIB_JOURNAL; rlJournalStart
		assertTrue "successfull '$CMD' adds exactly 1 passed test to journal" \
			"rlPhaseStart FAIL; $CMD ; rlPhaseEnd ; rlJournalPrintText |grep '1 *good'"
		rm $BEAKERLIB_JOURNAL; rlJournalStart
		assertTrue "successfull '$CMD' adds no failed test to journal" \
			"rlPhaseStart FAIL; $CMD ; rlPhaseEnd ;  rlJournalPrintText |grep '0 *bad'"
		rm $BEAKERLIB_JOURNAL; rlJournalStart
	else
		rm $BEAKERLIB_JOURNAL; rlJournalStart
		assertTrue "failed '$CMD' adds exactly 1 failed test to journal" \
			"rlPhaseStart FAIL; $CMD ; rlPhaseEnd ;  rlJournalPrintText |grep '1 *bad'"
		rm $BEAKERLIB_JOURNAL; rlJournalStart
		assertTrue "failed '$CMD' adds no passed test to journal" \
			"rlPhaseStart FAIL; $CMD ; rlPhaseEnd ;  rlJournalPrintText |grep '0 *good'"
		rm $BEAKERLIB_JOURNAL; rlJournalStart
	fi
}

#removes parameters from working assert call - must not pass
#only works for assert because it checks journal, not the exit code!
__low_on_parameters(){
	rm $BEAKERLIB_JOURNAL; rlJournalStart
	assertTrue "running '$1' (all parameters) must succeed" \
	"rlPhaseStart FAIL; $1 ; rlPhaseEnd ;  rlJournalPrintText |grep '1 *good'"
	local CMD=""
	for i in $1 ; do
		CMD="${CMD}${i} "
		if [ "x$CMD" == "x$1 " ] ; then break ; fi
		#echo "--$1-- --$CMD--"
		rm $BEAKERLIB_JOURNAL; rlJournalStart
		assertFalse "running just '$CMD' (missing parameters) must not succeed" \
	    "rlPhaseStart FAIL; $CMD ; rlPhaseEnd ;  rlJournalPrintText |grep '1 *good'"
	done
}

rhts-report-result(){
  echo "ANCHOR NAME: $1\nRESULT: $2\n LOGFILE: $3\nSCORE: $4"
}
