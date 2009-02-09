#!/bin/bash

# logging.sh - part of RHTS library
# Authors:  Chris Ward      <cward@redhat.com>
#           Ondrej Hudlicky <ohudlick@redhat.com>
#           Petr Muller     <pmuller@redhat.com> 
#
# Description: Contains routines for various logging inside RHTS tests
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

logging.sh - RHTSlib logging functions and support for phases

=head1 DESCRIPTION

Routines for creating various types of logs inside RHTS tests.
Implements also phase support with automatic assert evaluation.

=head1 FUNCTIONS

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__INTERNAL_LogText()
{
  local MESSAGE=${1:-"***BAD RHTSLIB_HLOG CALL***"}
  local LOGFILE=${2:-$OUTPUTFILE}
  [ -z "$LOGFILE" ] && LOGFILE=$( mktemp )
  [ ! -e "$LOGFILE" ] && touch "$LOGFILE"
  [ ! -w "$LOGFILE" ] && LOGFILE=$( mktemp )
  echo -e "$MESSAGE" | tee -a $LOGFILE
  return $?
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlLog*
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Logging

=head3 rlLog

=head3 rlLogDebug

=head3 rlLogInfo

=head3 rlLogWarning

=head3 rlLogError

=head3 rlLogFatal

Creates a time-labelled message in the log. There is a bunch of aliases which
can create messages formated as DEBUG/INFO/WARNING/ERROR or FATAL (but you
would probably want to use rlDie instead of the last one).

    rlLog message [logfile] [priority]

=over

=item message

Message you want to show (use quotes when invoking).

=item logfile

Log file. If not supplied, OUTPUTFILE is assumed.

=item priority

Priority of the log.

=back

=cut

rlLog()
{
  __INTERNAL_LogText ":: [`date +%H:%M:%S`] :: $3 $1" "$2"
  if [ "$3" == "" ]
  then
    rljAddMessage "$1" "LOG"
  fi
}

rlLogDebug()   { [ "$DEBUG" == 'true' -o "$DEBUG" == '1' -o "$LOG_LEVEL" == "DEBUG" ] && rlLog "$1" "$2" "[ DEBUG   ] ::" && rljAddMessage "$1" "DEBUG"; }
rlLogInfo()    { rlLog "$1" "$2" "[ INFO    ] ::"; rljAddMessage "$1" "INFO" ; }
rlLogWarning() { rlLog "$1" "$2" "[ WARNING ] ::"; rljAddMessage "$1" "WARNING" ; }
rlLogError()   { rlLog "$1" "$2" "[ ERROR   ] ::"; rljAddMessage "$1" "ERROR" ; }
rlLogFatal()   { rlLog "$1" "$2" "[ FATAL   ] ::"; rljAddMessage "$1" "FATAL" ; }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlDie
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlDie

Creates a time-labelled message in the log, reports test result,
uploads logs, closes not closed phase and terminates test.

    rlDie message [logfile] [testname] [result] [score] [file...]

=over

=item message

Message you want to show (use quotes when invoking).

=item logfile

Log file. If not supplied, OUTPUTFILE is assumed.

=item testname

Test name - for result reporting. Default is content of RHTS's \$TEST variable.

=item result

Test RESULT - for result reporting. Default is WARN.

=item score

Test SCORE - for result reporting. Default is 0.

=item file

Files (logs) you want to upload as well. C<rlBundleLogs> will be used for it.

=back

=cut

rlDie()
{
  local rlMSG="$1"
  local rlLOG="$2"
  local rlTEST=${3:-$TEST}
  local rlRESULT=${4:-WARN}
  local rlSCORE=${5:-0}
  [ -z "$@" ] && rlBundleLogs rlDieBundling $@
  rlLogFatal "$rlMSG" "$rlLOG"
  rlReport "$rlTEST" "$rlRESULT" "$rlSCORE"
  rlPhaseEnd
  exit 0
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlHeadLog
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# obsoleted by phases
# : <<=cut
# =pod
#
# =head2 rlHeadLog
#
# Creates a header in the supplied log
#
#  * parameter 1: message you want to show (use quotes when invoking)
#  * optional parameter 2: log file. If not supplied, OUTPUTFILE is assumed
# =cut

rlHeadLog()
{
  local text="$1"
  local logfile=${2:-""}
  __INTERNAL_LogText "\n::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::" "$logfile"
  rlLog "$text" "$logfile"
  __INTERNAL_LogText "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n" "$logfile"
  rlLogWarning "rlHeadLog is obsoleted, use rlPhase* instead"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlBundleLogs
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut 
=pod

=head3 rlBundleLogs

Create a tarball of files (e.g. logs) and attache them to the test result.

    rlBundleLogs package file [file...]

=over

=item package

Name of the package. Will be used as a part of the tar-ball name.

=item file

File(s) to be packed and submitted.

=back

Returns result of submiting the tarball.

=cut

rlBundleLogs(){
  local PKG=$1
  shift
  local BASE_NAME=$PKG.${JOBID}_${RECIPEID}_${TESTID}
  rlLog "Bundling logs" 

  if [ ! -d $BASE_NAME ]; then
    rlLogDebug "rlBundleLogs: Creating directory $BASE_NAME"
    mkdir $BASE_NAME
  fi

  for i in $@
  do
    rlLogInfo "rlBundleLogs: Adding $i"
    cp $i $BASE_NAME
    [ $? -eq 0 ] || rlLogError "rlBundleLogs: $i can't be packed"
  done
    
  tar zcvf $BASE_NAME.tar.gz $BASE_NAME &> /dev/null
  [ $? -eq 0 ] || rlLogError "rlBundleLogs: Packing wasn't successful"
  rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $BASE_NAME.tar.gz
  local SUBMITECODE=$?
  [ $SUBMITECODE -eq 0 ] || rlLogError "rlBundleLog: Submit wasn't  successful"
  rlLogDebug "rlBundleLogs: Removing tmps: $BASE_NAME, $BASE_NAME.tar.gz"
  rm -rf $BASE_NAME $BASE_NAME.tar.gz
  return $SUBMITECODE
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlShowPkgVersion
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Info

=head3 rlShowPackageVersion

Shows a message about version of packages.

    rlShowPackageVersion package [package...]

=over

=item package

Name of a package(s) you want to log.

=back

=cut

rlShowPackageVersion()
{
  local score=0
  if [ $# -eq 0 ]; then
    rlLogWarning "rlShowPackageVersion: Too few options"
    return 1
  fi
  for pkg in $@
  do
    if rpm -q $pkg &> /dev/null;
    then
      IFS=$'\n'
      for line in `rpm -q $pkg --queryformat "$pkg RPM version: %{version}-%{release}.%{arch}\n"`
      do
        rlLog $line
      done
      unset IFS
    else
      rlLogWarning "rlShowPackageVersion: Unable to locate package $pkg"
      let score+=1
    fi
  done
  [ $score -eq 0 ] && return 0 || return 1
}

# backward compatibility
rlShowPkgVersion() {
    rlLogWarning "rlShowPkgVersion is obsoleted by rlShowPackageVersion"
    rlShowPackageVersion $@;
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlShowRunningKernel
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlShowRunningKernel

Logs a message with version of the currently running kernel.

    rlShowRunningKernel

=cut

rlShowRunningKernel()
{
	rlLog "Kernel version: `uname -r`"
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPhaseStart
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Phases

=head3 rlPhaseStart

Starts a phase of a specific type. The final phase result is based
on all asserts included in the phase.  Do not forget to end phase
with C<rlPhaseEnd> when you are done.

    rlPhaseStart type [name]

=over

=item type

Type of the phase, one of the following:

=over

=item ABORT

When assert fails in this phase, test will be aborted.

=item FAIL

When assert fails here, phase will report a FAIL.

=item WARN

When assert fails here, phase will report a WARN.

=back

=item name

Optional name of the phase (if not provided, one will be generated).

=back

If all asserts included in the phase pass, phase reports PASS.

=cut

rlPhaseStart(){
  if [ "x$1" = "xABORT" -o "x$1" = "xFAIL" -o "x$1" = "xWARN" ] ; then
    rljAddPhase "$1" "$2"
  else
    rlLogError "rlPhaseStart: Unknown phase type: $1"
  fi
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPhaseEnd
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlPhaseEnd

Ends current phase.

    rlPhaseEnd

Final phase result is based on included asserts and phase type.

=cut

rlPhaseEnd(){
	rljClosePhase

	#this is for rcw integration
	if [ -x /usr/bin/rcw-copy-log ]
	then
		rlJournalPrint > /tmp/rhtslib-rcw-journal
		/usr/bin/rcw-copy-log /tmp/rhtslib-rcw-journal
	fi
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPhaseStart*
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlPhaseStartSetup

=head3 rlPhaseStartTest

=head3 rlPhaseStartCleanup

Starts a phase of a specific type: Setup -> ABORT, Test -> FAIL, Cleanup -> WARN.
Also provides some default phase names.

    rlPhaseStartSetup [name]
    rlPhaseStartTest [name]
    rlPhaseStartCleanup [name]

=over

=item name

Optional name of the phase.

=back

If you do not want these shortcuts, use plain C<rlPhaseStart> function.

=cut

rlPhaseStartSetup(){
	rljAddPhase "ABORT" "${1:-Setup}"
}
rlPhaseStartTest(){
	rljAddPhase "FAIL" "${1:-Test}"
}
rlPhaseStartCleanup(){
	rljAddPhase "WARN" "${1:-Cleannup}"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlLogLowMetric
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Metric

=head3 rlLogMetricLow

Logs a metric, which should be as low as possible (example: memory
consumption, run time) to the journal.

    rlLogMetricLow name value [tolerance]

=over

=item name

Name of the metric. It has to be unique in a phase.

=item value

Value of the metric.

=item tolerance

It is used when comparing via rcw. It means how larger can the
second value be to not trigger a FAIL. Default is 0.2

=back

When comparing FIRST, SECOND, then:

    FIRST >= SECOND means PASS
    FIRST+FIRST*tolerance >= SECOND means WARN
    FIRST+FIRST*tolerance < SECOND means FAIL

B<Example:> Simple benchmark is compared via this metric type in
rcw.  It has a tolerance of 0.2. First run had 1 second. So:

    For PASS, second run has to be better or equal to first. So any value of second or less is a PASS.
    For WARN, second run can be a little worse than first. Tolerance is 0.2, so anything lower than 1.2 means WARN.
    For FAIL, anything worse than 1.2 means FAIL.

=cut

rlLogMetricLow(){
    rljAddMetric "low" "$1" "$2" "$3"
}

rlLogLowMetric(){
    rlLogWarning "rlLogLowMetric is deprecated, use rlLogMetricLow instead"
    rljAddMetric "low" "$1" "$2" "$3"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlLogMetricHigh
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlLogMetricHigh

Logs a metric, which should be as high as possible (example:
number of executions per second) to the journal

    rlLogMetricHigh name value [tolerance]

=over

=item name

Name of the metric. It has to be unique in a phase.

=item value

Value of the metric.

=item tolerance

It is used when comparing via rcw. It means how lower can the
second value be to not trigger a FAIL. Default is 0.2

=back

When comparing FIRST, SECOND, then:

    FIRST <= SECOND means PASS
    FIRST+FIRST*tolerance <= SECOND means WARN
    FIRST+FIRST*tolerance > SECOND means FAIL

=cut

rlLogMetricHigh(){
    rljAddMetric "high" "$1" "$2" "$3"
}

rlLogHighMetric(){
    rlLogWarning "rlLogHighMetric is deprecated, use rlLogMetricHigh instead"
    rljAddMetric "high" "$1" "$2" "$3"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# AUTHORS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head1 AUTHORS

=over

=item *

Petr Muller <pmuller@redhat.com>

=item *

Jan Hutar <jhutar@redhat.com>

=item *

Ales Zelinka <azelinka@redhat.com>

=item *

Petr Splichal <psplicha@redhat.com>

=back

=cut
