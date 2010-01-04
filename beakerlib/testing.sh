#!/bin/bash

# testing.sh - part of BeakerLib
# Authors:  Ondrej Hudlicky <ohudlick@redhat.com>
#           Petr Muller     <pmuller@redhat.com> 
#
# Description: Contains helpers for various testing tasks
#
# Copyright (c) 2008 Red Hat, Inc. All rights reserved. This copyrighted material 
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

: <<=cut
=pod

=head1 NAME

testing.sh - BeakerLib functions for various testing tasks

=head1 DESCRIPTION

This file contains functions related directly to testing. These functions are
non-specialized asserts, as well as several other functions related to testing.  

=head1 FUNCTIONS

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#   Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

. $BEAKERLIB/logging.sh
. $BEAKERLIB/journal.sh

__INTERNAL_LogAndJournalPass(){
  rljAddTest "$1" "PASS"
}

__INTERNAL_LogAndJournalFail(){
  rljAddTest "$1 $2" "FAIL"
}

# __INTERNAL_ConditionalAssert comment status [failed-comment]
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__INTERNAL_ConditionalAssert(){
  if [ "$2" == "0" ]
  then
    __INTERNAL_LogAndJournalPass "$1" "$3"
    return 0
  else
    __INTERNAL_LogAndJournalFail "$1" "$3"
    return 1
  fi
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPass                                                                 
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut                                                                       
=pod                                                                           

=head2 Manual Asserts

=head3 rlPass

Manual assertion, asserts and logs PASS.

    rlPass comment

=over

=item comment

Short test summary.

=back

Returns 0 and asserts PASS.

=cut

rlPass(){
    __INTERNAL_LogAndJournalPass "$1"
    return 0
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlFail                                                                 
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut                                                                       
=pod                                                                           

=head3 rlFail

Manual assertion, asserts and logs FAIL.

    rlFail comment

=over

=item comment

Short test summary.

=back

Returns 1 and asserts FAIL.

=cut

rlFail(){
    __INTERNAL_LogAndJournalFail "$1"
    return 1
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssert0
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Arithmetic Asserts

=head3 rlAssert0

Assertion checking for the equality of parameter to zero.

    rlAssert0 comment value

=over

=item comment

Short test summary, e.g. "Test if compilation ended successfully".

=item value

Integer value (usually return code of a command).

=back

Returns 0 and asserts PASS when C<value == 0>.

=cut

rlAssert0(){
  __INTERNAL_ConditionalAssert "$1" "$2" "(Assert: expected 0, got $2)"
  return $?
} 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertEquals
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertEquals

Assertion checking for the equality of two parameters.

    rlAssertEquals comment value1 value2

=over

=item comment

Short test summary, e.g. "Test if all 3 packages have been downloaded".

=item value1

First parameter to compare, can be a number or a string

=item value2

Second parameter to compare, can be a number or a string

=back

Returns 0 and asserts PASS when C<value1 == value2>.

=cut

rlAssertEquals() {
  if [ -z "$3" ] ; then
    __INTERNAL_LogAndJournalFail "rlAssertEquals called without all needed parameters" ""
    return 1
  fi
  __INTERNAL_ConditionalAssert "$1" `[ "$2" == "$3" ]; echo $?` "(Assert: $2 should equal $3)"
  return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertNotEquals
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertNotEquals

Assertion checking for the non-equality of two parameters.

    rlAssertNotEquals comment value1 value2

=over

=item comment

Short test summary, e.g. "Test if return code is not 139".

=item value1

First parameter to compare, can be a number or a string

=item value2

Second parameter to compare, can be a number or a string

=back

Returns 0 and asserts PASS when C<value1 != value2>.

=cut

rlAssertNotEquals() {
  if [ -z "$3" ] ; then
    __INTERNAL_LogAndJournalFail "rlAssertNotEquals called without all needed parameters" ""
    return 1
  fi
  __INTERNAL_ConditionalAssert "$1" `[ "$2" != "$3" ]; echo $?` "(Assert: \"$2\" should not equal \"$3\")"
  return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertGreater
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertGreater

Assertion checking whether first parameter is greater than the second one.

    rlAssertGreater comment value1 value2

=over

=item comment

Short test summary, e.g. "Test whether there are running more instances of program."

=item value1

Integer value.

=item value2

Integer value.

=back

Returns 0 and asserts PASS when C<value1 E<gt> value2>.

=cut

rlAssertGreater() {
  __INTERNAL_ConditionalAssert "$1" `[ "$2" -gt "$3" ]; echo $?` "(Assert: \"$2\" should be greater than \"$3\")"
  return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertGreaterOrEqual
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertGreaterOrEqual

Assertion checking whether first parameter is greater or equal to the second one.

    rlAssertGreaterOrEqual comment value1 value2

=over

=item comment

Short test summary (e.g. "There should present at least one...")

=item value1

Integer value.

=item value2

Integer value.

=back

Returns 0 and asserts PASS when C<value1 E<gt>= value2>.

=cut

rlAssertGreaterOrEqual() {
  __INTERNAL_ConditionalAssert "$1" `[ "$2" -ge "$3" ]; echo $?` "(Assert: \"$2\" should be >= \"$3\")"
  return $?
}



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertExists
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 File Asserts

=head3 rlAssertExists

Assertion checking for the existence of a file.

    rlAssertExists file

=over

=item file

Path to the file.

=back

Returns 0 and asserts PASS when C<file> exists.

=cut

rlAssertExists(){
    if [ -z "$1" ] ; then
        __INTERNAL_LogAndJournalFail "rlAssertExists called without parameter" ""
        return 1
    fi
  __INTERNAL_ConditionalAssert "File $1 should exist" `[ -e "$1" ]; echo $?`
  return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertNotExists
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

: <<=cut
=pod

=head3 rlAssertNotExists

Assertion checking for the non-existence of a file.

    rlAssertNotExists file

=over

=item file

Path to the file.

=back

Returns 0 and asserts PASS when C<file> does not exist.

=cut

rlAssertNotExists(){
    if [ -z "$1" ] ; then
        __INTERNAL_LogAndJournalFail "rlAssertNotExists called without parameter" ""
        return 1
    fi
  __INTERNAL_ConditionalAssert "File $1 should not exist" `[ ! -e "$1" ]; echo $?`
  return $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertGrep
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertGrep

Assertion checking if the file contains a pattern.

    rlAssertGrep pattern file [options]

=over

=item pattern

Regular expression to be searched for.

=item file

Path to the file.

=item options

Optional parameters to be passed to grep, default is C<-q>. Can be
used to perform case insensitive matches (-i), or using
extended (-E) or perl (-P) regular expressions.

=back

Returns 0 and asserts PASS when C<file> exists and contains given
C<pattern>.

=cut

rlAssertGrep(){
    if [ ! -e "$2" ] ; then
        __INTERNAL_LogAndJournalFail "rlAssertGrep: failed to find file $2"
        return 2
    fi
    local options=${3:--q}
    grep $options "$1" "$2"
    __INTERNAL_ConditionalAssert "File '$2' should contain '$1'" $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertNotGrep
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertNotGrep

Assertion checking that the file does not contain a pattern.

    rlAssertNotGrep pattern file [options]

=over

=item pattern

Regular expression to be searched for.

=item file

Path to the file.

=item options

Optional parameters to be passed to grep, default is C<-q>. Can be
used to perform case insensitive matches (-i), or using
extended (-E) or perl (-P) regular expressions.

=back

Returns 0 and asserts PASS when C<file> exists and does not
contain given C<pattern>.

=cut
rlAssertNotGrep(){
    if [ ! -e "$2" ] ; then
        __INTERNAL_LogAndJournalFail "rlAssertNotGrep: failed to find file $2"
        return 2
    fi
    local options=${3:--q}
    ! grep $options "$1" "$2"
    __INTERNAL_ConditionalAssert "File '$2' should not contain '$1'" $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertDiffer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertDiffer

Assertion checking that two files differ (are not identical).

    rlAssertDiffer file1 file2

=over

=item file1

Path to first file1

=item file2

Path to second file

=back

Returns 0 and asserts PASS when C<file1> and C<file2> differs.

=cut

rlAssertDiffer(){ 
  for file in "$1" "$2"
  do
    if [ ! -e "$file" ]
    then
      __INTERNAL_LogAndJournalFail "rlAssertDiffer: file $file was not found"
      return 2
    fi
  done
  ! cmp -s "$1" "$2"
  __INTERNAL_ConditionalAssert "Files $1 and $2 should differ" $?
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertNotDiffer
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertNotDiffer

Assertion checking that two files do not differ (are identical).

    rlAssertNotDiffer file1 file2

=over

=item file1

Path to first file1

=item file2

Path to second file

=back

Returns 0 and asserts PASS when C<file1> and C<file2> do not differ.

=cut

rlAssertNotDiffer(){
  for file in "$1" "$2"
  do
    if [ ! -e "$file" ]
    then
      __INTERNAL_LogAndJournalFail "rlAssertNotDiffer: file $file was not found"
      return 2
    fi
  done

  cmp -s "$1" "$2"
  __INTERNAL_ConditionalAssert "Files $1 and $2 should not differ" $?
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlRun
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Run, Watch, Report

=head3 rlRun

Run command with optional comment and make sure its exit code
matches expectations.

    rlRun [-t] [-l] command [status[,status...]] [comment]

=over

=item -t

If specified, stdout and stderr of the command output will be tagged
with strigs 'STDOUT: ' and 'STDERR: '.

=item -l

If specified, output of the command (tagged, if -t was specified) is
logged using rlLog function.

=item command

Command to run.

=item status

Expected exit code(s). Optional, default 0. If you expect more
exit codes, separate them with comma (e.g. "0,1" when both 0 and 1
are OK and expected), or use from-to notation (i.e. "2-5" for "2,3,4,5"),
or combine them (e.g. "2-4,26" for "2,3,4,26").

=item comment

Short summary describing the action (optional, but recommended -
explain what are you doing here).

=back

Returns the exit code of the command run. Asserts PASS when
command's exit status is in the list of expected exit codes.

Note: The output of rlRun is buffered when using C<-t> or C<-l>
option (they use unix pipes, which are buffered by nature). If you
need an unbuffered output just make sure that C<expect> package is
installed on your system (its "unbuffer" tool will automatically
be used to produce unbuffered output).

=cut

rlRun(){

  GETOPT=`getopt -q -o lt -- "$@"`
  eval set -- "$GETOPT"
  
  local DO_LOG=false
  local DO_TAG=false
  local TAG_OUT=''
  local TAG_ERR=''
  local LOG_FILE='/dev/null'
  
  while true ; do
    case "$1" in
      -l)
            DO_LOG=true;
            LOG_FILE=`mktemp`
            shift;;
      -t)
            DO_TAG=true;
            TAG_OUT='STDOUT: '
            TAG_ERR='STDERR: '
            shift
            ;;
      --)  shift; break;;
      *)   shift;;
    esac
  done

  local command=$1
  local expected_orig=${2:-0}
  local expected=${2:-0}
  local comment=${3:-"Running '$command'"}

  # in case expected exit code is provided as "2-5,26", expand it to "2,3,4,5,26"
  while echo "$expected" | grep -q '[0-9]-[0-9]'; do
    local interval=$(echo "$expected" | sed "s/.*\(\<[0-9]\+-[0-9]\+\>\).*/\1/")
    if [ -z "$interval" ]; then
      rlLogWarning "rlRun: Something happened when getting interval, using '0-0'"
      interval='0-0'
    fi
    local interval_a=$(echo "$interval" | cut -d '-' -f 1)
    local interval_b=$(echo "$interval" | cut -d '-' -f 2)
    if [ -z "$interval_a" -o -z "$interval_b" ]; then
      rlLogWarning "rlRun: Something happened when getting boundaries of interval, using '0' and '0'"
      interval_a=0
      interval_b=0
    fi
    if [ $interval_a -gt $interval_b ]; then
      rlLogWarning "rlRun: First boundary have to be smaller then second one, using '$interval_b' and '$interval_b'"
      interval_a=$interval_b
    fi
    local replacement="$interval_a"
    let interval_a=$interval_a+1
    for i in $(seq $interval_a $interval_b); do
      replacement="$replacement,$i"
    done
    expected=$(echo "$expected" | sed "s/$interval/$replacement/")
  done

  rlLogDebug "rlRun: Running command: $command"
  
  if $DO_LOG || $DO_TAG; then
    local UNBUFFER=''
    if which unbuffer 1>/dev/null 2>&1; then
        UNBUFFER='unbuffer '
    fi
    eval "$UNBUFFER$command" 2> >(sed -u -e "s/^/$TAG_ERR/g" | tee -a $LOG_FILE) 1> >(sed -u -e "s/^/$TAG_OUT/g" | tee -a $LOG_FILE)
  else
    eval "$command"
  fi
  local exitcode=$?
  sync
  if $DO_LOG; then
    rlLog "$command\n`cat $LOG_FILE`"
    rm $LOG_FILE
  fi
  
  rlLogDebug "rlRun: Command finished with exit code: $exitcode, expected: $expected_orig"
  echo "$expected" | grep -q "\<$exitcode\>"   # symbols \< and \> match the empty string at the beginning and end of a word
  __INTERNAL_ConditionalAssert "$comment" $? "(Expected $expected_orig, got $exitcode)"
  
  return $exitcode
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlWatchdog
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlWatchdog

Run C<command>. If it does not finish in specified time, then kill
it using C<signal>.

    rlWatchdog command timeout [signal]

=over

=item command

Command to run.

=item timeout

Timeout to wait, in seconds.

=item signal

Signal to use (optional, default KILL).

=back

Returns 0 if the command ends normally, without need to be killed.

=cut

rlWatchdog(){
	local command=$1
	local timeout=$2
	local killer=${3:-"KILL"}
	rm -f __INTERNAL_FINISHED __INTERNAL_TIMEOUT
	rlLog "Runnning $command, with $timeout seconds timeout"
	eval "$command; touch __INTERNAL_FINISHED" &
	pidcmd=$!
	eval "sleep $timeout; touch __INTERNAL_TIMEOUT" &
	pidsleep=$!

	while true
	do
		if [ -e __INTERNAL_FINISHED ]
		then
			rlLog "Comand ended itself, do not killing"
			kill $pidsleep
			sleep 1
			rm -f __INTERNAL_FINISHED __INTERNAL_TIMEOUT
			return 0
		elif [ -e __INTERNAL_TIMEOUT ]
		then
			rlLog "Command still running, killing with $killer"
			kill -$killer $pidcmd
			sleep 1
			rm -f __INTERNAL_FINISHED __INTERNAL_TIMEOUT
			return 1
		fi
		sleep 1
	done
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlReport
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlReport

Report test result using RHTS C<rhts-report-result> function.

    rlReport name result [score] [log]

=over

=item name

Name of the test result.

=item result

Result (one of PASS, WARN, FAIL). If called with something
else, will use WARN.

=item score

Test score (optional).

=item log

Optional log file to be submitted instead of default C<OUTPUTFILE>.

=back

=cut

rlReport(){
    # only PASS/WARN/FAIL is allowed
    local testname="$1"
    local result="$(echo $2 | tr '[:lower:]' '[:upper:]')"
    local score="$3"
    local logfile=${4:-$OUTPUTFILE}
    case "$result" in
          'PASS' | 'PASSED' | 'PASSING' ) result='PASS'; ;;
          'FAIL' | 'FAILED' | 'FAILING') result='FAIL'; ;;
          'WARN' | 'WARNED' | 'WARNING') result='WARN'; ;;
          'ABORT') result='WARN';;
          *)
            rlLogWarning "rlReport: Only PASS/WARN/FAIL results are possible."
            result='WARN'
          ;;
        esac
    rlLogDebug "rlReport: result: $result, score: $score, log: $logfile"
    # report the result only if TESTID is set
    if [ -n "$TESTID" ] ; then
        rhts-report-result "$testname" "$result" "$logfile" "$score" \
            || rlLogError "rlReport: Failed to report the result"
    fi
}



: <<=cut
=pod

=head1 AUTHORS

=over

=item *

Ondrej Hudlicky <ohudlick@redhat.com>

=item *

Petr Muller <pmuller@redhat.com>

=item *

Jan Hutar <jhutar@redhat.com>

=item *

Petr Splichal <psplicha@redhat.com>

=item *

Ales Zelinka <azelinka@redhat.com>

=back

=cut
