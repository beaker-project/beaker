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

test_rlAssertDiffer() {
  local FILE1="`mktemp`"
  local FILE2="`mktemp`"
  local FILE3="`mktemp '/tmp/test rlAssertDiffer3-XXXXXX'`"

  echo "AAA" > "$FILE1"
  echo "AAA" > "$FILE2"
  echo "AAA" > "$FILE3"

  assertFalse "rlAssertDiffer does not return 0 for the identical files"\
  "rlAssertDiffer $FILE1 $FILE2"
  __one_fail_one_pass "rlAssertDiffer $FILE1 $FILE2" FAIL

  assertFalse "rlAssertDiffer does not return 0 for the identical files with spaces in name"\
  "rlAssertDiffer \"$FILE1\" \"$FILE3\""
  __one_fail_one_pass "rlAssertDiffer \"$FILE1\" \"$FILE3\"" FAIL

  assertFalse "rlAssertDiffer does not return 0 for the same file"\
  "rlAssertDiffer $FILE1 $FILE1"
  __one_fail_one_pass "rlAssertDiffer $FILE1 $FILE1" FAIL

  assertFalse "rlAssertDiffer does not return 0 when called without parameters"\
  "rlAssertDiffer"

  assertFalse "rlAssertDiffer does not return 0 when called with only one parameter"\
  "rlAssertDiffer $FILE1"

  echo "BBB" > "$FILE3"
  echo "BBB" > "$FILE2"

  assertTrue "rlAssertDiffer returns 0 for different files"\
  "rlAssertDiffer $FILE1 $FILE2"
  __one_fail_one_pass "rlAssertDiffer $FILE1 $FILE2" PASS

  assertTrue "rlAssertDiffer returns 0 for different files with space in name"\
  "rlAssertDiffer \"$FILE1\" \"$FILE3\""
  __one_fail_one_pass "rlAssertDiffer \"$FILE1\" \"$FILE3\"" PASS
  rm -f "$FILE1" "$FILE2" "$FILE3"
}

test_rlAssertNotDiffer() {
  local FILE1="`mktemp`"
  local FILE2="`mktemp`"
  local FILE3="`mktemp '/tmp/test rlAssertNotDiffer3-XXXXXX'`"

  echo "AAA" > "$FILE1"
  echo "AAA" > "$FILE2"
  echo "AAA" > "$FILE3"

  assertTrue "rlAssertNotDiffer returns 0 for the identical files"\
  "rlAssertNotDiffer $FILE1 $FILE2"
  __one_fail_one_pass "rlAssertNotDiffer $FILE1 $FILE2" PASS

  assertTrue "rlAssertNotDiffer returns 0 for the identical files with spaces in name"\
  "rlAssertNotDiffer \"$FILE1\" \"$FILE3\""
  __one_fail_one_pass "rlAssertNotDiffer \"$FILE1\" \"$FILE3\"" PASS

  assertTrue "rlAssertNotDiffer returns 0 for the same file"\
  "rlAssertNotDiffer $FILE1 $FILE1"
  __one_fail_one_pass "rlAssertNotDiffer $FILE1 $FILE1" PASS

  assertFalse "rlAssertNotDiffer does not return 0 when called without parameters"\
  "rlAssertNotDiffer"

  assertFalse "rlAssertNotDiffer does not return 0 when called with only one parameter"\
  "rlAssertNotDiffer $FILE1"

  echo "BBB" > "$FILE3"
  echo "BBB" > "$FILE2"

  assertFalse "rlAssertNotDiffer does not return 0 for different files"\
  "rlAssertNotDiffer $FILE1 $FILE2"
  __one_fail_one_pass "rlAssertNotDiffer $FILE1 $FILE2" FAIL

  assertFalse "rlAssertNotDiffer does not return 0 for different files with space in name"\
  "rlAssertNotDiffer \"$FILE1\" \"$FILE3\""
  __one_fail_one_pass "rlAssertNotDiffer \"$FILE1\" \"$FILE3\"" FAIL
  rm -f "$FILE1" "$FILE2" "$FILE3"
}


test_rlAssertExists() {
	local FILE="/tmp/test_rlAssertExists"

	touch $FILE
    assertTrue "rlAssertExists returns 0 on existing file" \
    "rlAssertExists $FILE"
	__one_fail_one_pass "rlAssertExists $FILE" PASS

	rm -f $FILE
    assertFalse "rlAssertExists returns 1 on non-existant file" \
    "rlAssertExists $FILE"
	__one_fail_one_pass "rlAssertExists $FILE" FAIL
    assertFalse "rlAssertExists returns 1 when called without arguments" \
    "rlAssertExists"

    local FILE="/tmp/test rlAssertExists filename with spaces"
	touch "$FILE"
    assertTrue "rlAssertExists returns 0 on existing file with spaces in its name" \
    "rlAssertExists \"$FILE\""
    rm -f "$FILE"
}
test_rlAssertNotExists() {
    local FILE="/tmp/test_rlAssertNotExists filename with spaces"
    local FILE2="/tmp/test_rlAssertNotExists"
	touch "$FILE"
    assertFalse "rlAssertNotExists returns 1 on existing file" \
    "rlAssertNotExists \"$FILE\""
	__one_fail_one_pass "rlAssertNotExists \"$FILE\"" FAIL
    assertFalse "rlAssertNotExists returns 1 when called without arguments" \
    "rlAssertNotExists"

	rm -f "$FILE"
	touch "$FILE2"
    assertTrue "rlAssertNotExists returns 0 on non-existing file" \
    "rlAssertNotExists \"$FILE\""
	__one_fail_one_pass "rlAssertNotExists \"$FILE\"" PASS
	rm -f "$FILE2"

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
    # without optional parameter
    assertTrue "rlAssertGrep without optional arg should not ignore case" \
        'rlAssertGrep YES grepfile; [ $? == 1 ]'
    assertTrue "rlAssertGrep without optional arg should ignore extended regexp" \
        'rlAssertGrep "e{1,3}" grepfile; [ $? == 1 ]'
    assertTrue "rlAssertGrep without optional arg should ignore perl regexp" \
        'rlAssertGrep "\w+" grepfile; [ $? == 1 ]'
    # with optional parameter
    assertTrue "rlAssertGrep with -i should ignore case" \
        'rlAssertGrep YES grepfile -i; [ $? == 0 ]'
    assertTrue "rlAssertGrep with -E should use extended regexp" \
        'rlAssertGrep "e{1,3}" grepfile -E; [ $? == 0 ]'
    assertTrue "rlAssertGrep with -P should use perl regexp" \
        'rlAssertGrep "\w+" grepfile -P; [ $? == 0 ]'
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
    # without optional parameter
    assertTrue "rlAssertNotGrep without optional arg should not ignore case" \
        'rlAssertNotGrep YES grepfile; [ $? == 0 ]'
    assertTrue "rlAssertNotGrep without optional arg should ignore extended regexp" \
        'rlAssertNotGrep "e{1,3}" grepfile; [ $? == 0 ]'
    assertTrue "rlAssertNotGrep without optional arg should ignore perl regexp" \
        'rlAssertNotGrep "\w+" grepfile; [ $? == 0 ]'
    # with optional parameter
    assertTrue "rlAssertNotGrep with -i should ignore case" \
        'rlAssertNotGrep YES grepfile -i; [ $? == 1 ]'
    assertTrue "rlAssertNotGrep with -E should use extended regexp" \
        'rlAssertNotGrep "e{1,3}" grepfile -E; [ $? == 1 ]'
    assertTrue "rlAssertNotGrep with -P should use perl regexp" \
        'rlAssertNotGrep "\w+" grepfile -P; [ $? == 1 ]'
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
    
    rlRun -t 'echo "foobar1"' | grep "^STDOUT: foobar1" 1>/dev/null
    assertTrue "rlRun tagging (stdout)" "[ $? -eq 0 ]"

    rlRun -t 'echo "foobar2" 1>&2' | grep "^STDERR: foobar2"  1>/dev/null
    assertTrue "rlRun tagging (stderr)" "[ $? -eq 0 ]"
 
    OUTPUTFILE_orig="$OUTPUTFILE"
    export OUTPUTFILE="`mktemp`"
    
    rlRun -l 'echo "foobar3"' 2>&1 1>/dev/null
    grep 'echo "foobar3"' $OUTPUTFILE 1>/dev/null && egrep '^foobar3' $OUTPUTFILE 1>/dev/null
    assertTrue "rlRun logging plain" "[ $? -eq 0 ]"

    rlRun -l -t 'echo "foobar4"' 2>&1 1>/dev/null
    grep 'echo "foobar4"' $OUTPUTFILE 1>/dev/null && egrep '^STDOUT: foobar4' $OUTPUTFILE 1>/dev/null
    assertTrue "rlRun logging with tagging (stdout)" "[ $? -eq 0 ]"

    rlRun -l -t 'echo "foobar5" 1>&2' 2>&1 1>/dev/null
    grep 'echo "foobar5" 1>&2' $OUTPUTFILE 1>/dev/null && egrep '^STDERR: foobar5' $OUTPUTFILE 1>/dev/null
    assertTrue "rlRun logging with tagging (stderr)" "[ $? -eq 0 ]"

    #cleanup
    rm -rf $OUTPUTFILE
    export OUTPUTFILE="$OUTPUTFILE_orig"
}


test_rlWatchdog(){
	assertTrue "rlWatchDog detects when command end itself" 'rlWatchdog "sleep 3" 10'
	assertFalse "rlWatchDog kills command when time is up" 'rlWatchdog "sleep 10" 3'
	assertFalse "running rlWatchdog without timeout must not succeed" 'rlWatchDog "sleep 3"'
	assertFalse "running rlWatchdog without any parameters must not succeed" 'rlWatchDog '
}

test_rlFail(){
    assertFalse "This should always fail" "rlFail 'sometext'"
    __one_fail_one_pass "rlFail 'sometext'" FAIL
}

test_rlPass(){
    assertTrue "This should always pass" "rlPass 'sometext'"
    __one_fail_one_pass "rlPass 'sometext'" PASS
}

test_rlReport(){
	#placeholder for making  testCoverage ignore this helper
  rlJournalStart
  rlPhaseStartSetup
  for res in PASS FAIL WARN
  do
    OUT="`rlReport TEST $res | grep ANCHOR`"
    assertTrue "testing basic rlReport functionality" "[ \"$OUT\" == \"ANCHOR NAME: TEST\nRESULT: $res\n LOGFILE: $OUTPUTFILE\nSCORE: \" ]"
    OUT="`rlReport \"TEST TEST\" $res | grep ANCHOR`"
    assertTrue "testing if rlReport can handle spaces in test name" "[ \"$OUT\" == \"ANCHOR NAME: TEST TEST\nRESULT: $res\n LOGFILE: $OUTPUTFILE\nSCORE: \" ]"
    OUT="`rlReport \"TEST\" $res 5 \"/tmp/logname\" | grep ANCHOR`"
    assertTrue "testing if rlReport can handle all arguments" "[ \"$OUT\" == \"ANCHOR NAME: TEST\nRESULT: $res\n LOGFILE: /tmp/logname\nSCORE: 5\" ]"
    OUT="`rlReport \"TEST TEST\" $res 8 \"/tmp/log name\" | grep ANCHOR`"
    assertTrue "testing if rlReport can handle spaces in test name and log file" "[ \"$OUT\" == \"ANCHOR NAME: TEST TEST\nRESULT: $res\n LOGFILE: /tmp/log name\nSCORE: 8\" ]"
  done
  rlPhaseEnd
}
