#!/bin/bash
# performance.sh - part of BeakerLib
# Authors: 	Petr Muller     <pmuller@redhat.com> 
#
# Description: Contains performance measuring routines
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

performance.sh - BeakerLib functions for performance measuring

=head1 DESCRIPTION

This is a library of helpers and shortcut for performance monitoring
of applications. It provides various means of measuring time
and memory performance of programs.

=head1 FUNCTIONS

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPerfTime_RunsInTime
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Time Performance

=head3 rlPerfTime_RunsInTime

Measures, how many runs of some commands can be done in specified time.
This approach is suitable for short-time running tasks (up to few seconds),
where averaging few runs is not precise. This is done several times, and
the final result is the average of all runs. It prints the number on stdout,
so it has to be captured.

    rlPerfTime_RunsInTime command [time] [runs]

=over

=item command

Command to run.

=item time

Time in seconds (optional, default=30).

=item runs

Number of averaged runs (optional, default=3).

=back

=cut

rlPerfTime_RunsInTime(){
	local command=$1
  	local time=${2:-"30"}
  	local runs=${3:-"3"}
  	local RES=$((0))
  	local TOTAL=$((0))
  	local DONE_RUNS=$((1))
  	local PID=$$
  	rlLog "Measuring how much runs we'll make in $time seconds"
  	rlLog "Command: '$command'"
  	rlLog "The result is an average of $runs rounds"
  	trap '  TOTAL=$((TOTAL+RES));\
  			rlLog "Round $DONE_RUNS finished, made $RES runs in it";\
          	if [ "$DONE_RUNS" == "$runs" ];\
          	then\
          		rlLog "Done, the average ($TOTAL/$DONE_RUNS) is $((TOTAL/DONE_RUNS)) runs";\
            	echo $((TOTAL/DONE_RUNS));\
            	return 0;\
          	else\
            	RES=$((0));\
            	DONE_RUNS=$((DONE_RUNS+1));\
            	eval "sleep $time; kill -USR1 $PID" &
          	fi' SIGUSR1

  	eval "sleep $time; kill -USR1 $$" &
  	while true
  	do
    	eval "$1"
    	RES=$((RES+1))
  	done
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlPerfTime_AvgFromRuns
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlPerfTime_AvgFromRuns

Measures the average time of running some task. This approach is suitable
for long-time running tasks (tens of seconds and more), where it is
precise enough. Measured runs can be preceded by dry run, which is not
measured and it's purpose is to warm up various caches.
It prints the number on stdout, so it has to be captured.
Or, result is then stored in special rl_retval variable.

    rlPerfTime_AvgFromRuns command [count] [warmup]

=over

=item command

Command to run.

=item count

Times to run (optional, default=3).

=item warmup

Warm-up run, run if this option is not "warmup" (optional, default="warmup")

=back

=cut

rlPerfTime_AvgFromRuns(){
	local command="$1"
	local runs=${2:-"3"}
	local warmup=${3:-"warmup"}
	local total=0
	rlLog "Measuring the average time of runnning command '$command'"
	rlLog "The result will be an average of $runs runs"
		
	if [ "$warmup" == "warmup" ]
	then
		rlLog "Doing non-measured warmup run"
		eval "$command"
	fi
	local __INTERNAL_TIMER=`mktemp`
	for cnt in `seq $runs`
	do
		/usr/bin/time -o $__INTERNAL_TIMER -f "bt=\"%U + %S\"" $command
		. $__INTERNAL_TIMER
		rlLog "Run $cnt took $bt seconds"
		total="`echo "scale=5; $total + $bt" | bc`"		
	done
	rlLog "The average of $runs runs was `echo "scale=5; $total / $runs" | bc` seconds"
	echo "`echo "scale=5; $total / $runs" | bc`"
	export rl_retval="`echo "scale=5; $total / $runs" | bc`"
	rm -f $__INTERNAL_TIMER
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

=back

=cut
