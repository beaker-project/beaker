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

test_rlAssertExists() {
	local FILE="/tmp/test_rlAssertExists"

	touch $FILE
    assertTrue "rlAssertExists returns 0 on existing file" \
    "rlAssertExists $FILE"
	__one_fail_one_pass 'rlAssertExists $FILE' PASS

	rm -f $FILE
    assertFalse "rlAssertExists returns 1 on non-existant file" \
    "rlAssertExists $FILE"
	__one_fail_one_pass 'rlAssertExists $FILE' FAIL
    assertFalse "rlAssertExists returns 1 when called without arguments" \
    "rlAssertExists"
}
test_rlAssertNotExists() {
	local FILE="/tmp/test_rlAssertNotExists"

	touch $FILE
    assertFalse "rlAssertNotExists returns 1 on existing file" \
    "rlAssertNotExists $FILE"
	__one_fail_one_pass 'rlAssertNotExists $FILE' FAIL
    assertFalse "rlAssertNotExists returns 1 when called without arguments" \
    "rlAssertNotExists"

	rm -f $FILE
    assertTrue "rlAssertNotExists returns 0 on non-existing file" \
    "rlAssertNotExists $FILE"
	__one_fail_one_pass 'rlAssertNotExists $FILE' PASS
}

test_rlAssertGrep() {
    echo yes > grepfile
    assertTrue "rlAssertGrep should pass when pattern present" \
        'rlAssertGrep yes grepfile; [ $? == 0 ]'
	__one_fail_one_pass 'rlAssertGrep yes grepfile' PASS
	__one_fail_one_pass 'rlAssertGrep no grepfile' FAIL
	__low_on_parameters 'rlAssertGrep yes grepfile'
    assertTrue "rlAssertGrep should return 1 when pattern is not present" \
        'rlAssertGrep no grepfile; [ $? == 1 ]'
    assertTrue "rlAssertGrep should return 2 when file does not exist" \
        'rlAssertGrep no badfile; [ $? == 2 ]'
	__one_fail_one_pass 'rlAssertGrep yes badfile' FAIL
    rm -f grepfile
}

test_rlAssertNotGrep() {
    echo yes > grepfile
    assertTrue "rlAssertNotGrep should pass when pattern is not present" \
        'rlAssertNotGrep no grepfile; [ $? == 0 ]'
	__one_fail_one_pass 'rlAssertNotGrep no grepfile' PASS
	__one_fail_one_pass 'rlAssertNotGrep yes grepfile' FAIL
	__low_on_parameters 'rlAssertNotGrep no grepfile'
    assertTrue "rlAssertNotGrep should return 1 when pattern present" \
        'rlAssertNotGrep yes grepfile; [ $? == 1 ]'
    assertTrue "rlAssertNotGrep should return 2 when file does not exist" \
        'rlAssertNotGrep no badfile; [ $? == 2 ]'
	__one_fail_one_pass 'rlAssertNotGrep yes badfile' FAIL
    rm -f grepfile
}


test_rlAssert0() {
	__one_fail_one_pass 'rlAssert0 "abc" 0' PASS
	__one_fail_one_pass 'rlAssert0 "abc" 1' FAIL
	__low_on_parameters 'rlAssert0 "comment" 0'
}

test_rlAssertEquals(){
	__one_fail_one_pass 'rlAssertEquals "abc" "hola" "hola"' PASS
	__one_fail_one_pass 'rlAssertEquals "abc" "hola" "Hola"' FAIL
	__low_on_parameters 'rlAssertEquals comment hola hola'
}
test_rlAssertNotEquals(){
	__one_fail_one_pass 'rlAssertNotEquals "abc" "hola" "hola"' FAIL
	__one_fail_one_pass 'rlAssertNotEquals "abc" "hola" "Hola"' PASS
	__low_on_parameters 'rlAssertNotEquals comment hola Hola'
}

test_rlAssertGreater(){
	__one_fail_one_pass 'rlAssertGreater "comment" 999 1' PASS
	__one_fail_one_pass 'rlAssertGreater "comment" 1 -1' PASS
	__one_fail_one_pass 'rlAssertGreater "comment" 999 999' FAIL
	__one_fail_one_pass 'rlAssertGreater "comment" 10 100' FAIL
	__low_on_parameters 'rlAssertGreater comment -1 -2'
}
test_rlAssertGreaterOrEqual(){
	__one_fail_one_pass 'rlAssertGreaterOrEqual "comment" 999 1' PASS
	__one_fail_one_pass 'rlAssertGreaterOrEqual "comment" 1 -1' PASS
	__one_fail_one_pass 'rlAssertGreaterOrEqual "comment" 999 999' PASS
	__one_fail_one_pass 'rlAssertGreaterOrEqual "comment" 10 100' FAIL
	__low_on_parameters 'rlAssertGreaterOrEqual comment 10 10'
}

test_rlRun(){
	__one_fail_one_pass 'rlRun /bin/true 0 comment' PASS
	__one_fail_one_pass 'rlRun /bin/true 3 comment' FAIL
    assertTrue "rlRun with 1st parameter only assumes status = 0 " \
        'rlRun /bin/true'
	#more than one status
	__one_fail_one_pass 'rlRun /bin/true 0,1,2 comment' PASS
	__one_fail_one_pass 'rlRun /bin/true 1,0,2 comment' PASS
	__one_fail_one_pass 'rlRun /bin/true 1,2,0 comment' PASS
	__one_fail_one_pass 'rlRun /bin/true 10,100,1000 comment' FAIL
	# more than one status with interval
	__one_fail_one_pass 'rlRun /bin/false 0-2 comment' PASS
	__one_fail_one_pass 'rlRun /bin/false 5,0-2 comment' PASS
	__one_fail_one_pass 'rlRun /bin/false 0-2,5 comment' PASS
	__one_fail_one_pass 'rlRun /bin/false 5,0-2,7 comment' PASS
	__one_fail_one_pass 'rlRun /bin/false 5-10,0-2 comment' PASS
	__one_fail_one_pass 'rlRun /bin/false 0-2,5-10 comment' PASS

}


test_rlWatchdog(){
	assertTrue "rlWatchDog detects when command end itself" 'rlWatchdog "sleep 3" 10'
	assertFalse "rlWatchDog kills command when time is up" 'rlWatchdog "sleep 10" 3'
	assertFalse "running rlWatchdog without timeout must not succeed" 'rlWatchDog "sleep 3"'
	assertFalse "running rlWatchdog without any parameters must not succeed" 'rlWatchDog '
}

test_rlReport(){
	#placeholder for making  testCoverage ignore this helper
	echo "no idea how to test rlReport"
}
