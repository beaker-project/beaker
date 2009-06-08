#!/bin/bash

# logging.sh - part of BeakerLib
# Authors:  Chris Ward      <cward@redhat.com>
#           Ondrej Hudlicky <ohudlick@redhat.com>
#           Petr Muller     <pmuller@redhat.com> 
#
# Description: Contains routines for various logging inside Beaker tests
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

logging.sh - BeakerLib logging functions and support for phases

=head1 DESCRIPTION

Routines for creating various types of logs inside BeakerLib tests.
Implements also phase support with automatic assert evaluation.

=head1 FUNCTIONS

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__INTERNAL_LogText()
{
  local MESSAGE=${1:-"***BAD BEAKERLIB_HLOG CALL***"}
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
uploads logs, closes unfinished phase and terminates test.

    rlDie message [file...]

=over

=item message

Message you want to show (use quotes when invoking) - this
option is mandatory.

=item file

Files (logs) you want to upload as well. C<rlBundleLogs>
will be used for it. Files which are not readable will be
excluded before calling C<rlBundleLogs>, so it is safe to
call even with possibly not existent logs and it will
succeed.

=back

=cut

rlDie()
{
  # handle mandatory comment
  local rlMSG="$1"
  shift
  # handle optional list of logs
  if [ -n "$*" ]; then
    local logs=''
    for log in "$@"; do
      [ -r "$log" ] && logs="$logs $log"
    done
    [ -n "$logs" ] && rlBundleLogs rlDieLogsBundling $logs
  fi
  # do the work
  rlLogFatal "$rlMSG"
  rlAssert0 "$rlMSG" 1
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
    local i_new="$( echo $i | sed 's|[/ ]|_|g' )"
    while [ -e "$BASE_NAME/$i_new" ]; do
      i_new="${i_new}_next"
    done
    rlLogInfo "rlBundleLogs: Adding '$i' as '$i_new'"
    cp "$i" "$BASE_NAME/$i_new"
    [ $? -eq 0 ] || rlLogError "rlBundleLogs: '$i' can't be packed"
  done
    
  tar zcvf $BASE_NAME.tar.gz $BASE_NAME &> /dev/null
  [ $? -eq 0 ] || rlLogError "rlBundleLogs: Packing wasn't successful"
  rhts_submit_log -S "$RESULT_SERVER" -T "$TESTID" -l "$BASE_NAME.tar.gz"
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
# rlGetArch
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlGetArch

Returns base arch for the current system (good when you need
base arch on a multilib system).

    rlGetArch

On an i686 system you will get i386, on a ppc64 you will get ppc.

=cut


function rlGetArch() {
  local archi=$( uname -i 2>/dev/null || uname -m )
  case "$archi" in
    i486,i586,i686)
      archi='i386'
    ;;
    ppc64)
      archi='ppc'
    ;;
    '')
      rlLogWarning "rlGetArch: Do not know what the arch is ('$(uname -a)'), guessing 'i386'"
      archi='i386'
    ;;
  esac
  rlLogDebug "rlGetArch: This is architecture '$archi'"
  echo "$archi"
}



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlGetDistroRelease, rlGetDistroVariant
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlGetDistroRelease

=head3 rlGetDistroVariant

Returns release or variant of the distribution on the system

    rlGetDistroRelease
    rlGetDistroVariant

For example on the RHEL-4-AS you will get release 4 and variant AS,
on the RHEL-5-Client you will get release 5 and variant Client.

=cut

function __rlGetDistroVersion() {
  local version=0
  if rpm -q redhat-release &>/dev/null; then
    version=$( rpm -q --qf="%{VERSION}" redhat-release )
  elif rpm -q fedora-release &>/dev/null; then
    version=$( rpm -q --qf="%{VERSION}" fedora-release )
  elif rpm -q centos-release &>/dev/null; then
    version=$( rpm -q --qf="%{VERSION}" centos-release )
  fi
  rlLogDebug "__rlGetDistroVersion: This is distribution version '$version'"
  echo "$version"
}
function rlGetDistroRelease() {
  __rlGetDistroVersion | sed "s/^\([0-9]\+\)[^0-9]\+.*$/\1/"
}
function rlGetDistroVariant() {
  __rlGetDistroVersion | sed "s/^[0-9]\+\(.*\)$/\1/"
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
	rljAddPhase "WARN" "${1:-Cleanup}"
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
