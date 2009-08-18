#!/bin/bash

# virtualX.sh - part of BeakerLib
# Authors:      Jan Hutar <jhutar@redhat.com>
#
# Description: Contains helpers for starting/stopping virtual X server
#
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

: <<=cut
=pod

=head1 NAME

virtualX.sh - BeakerLib functions for manipulating with virtual X server

=head1 DESCRIPTION

This bash library is intended to provide simple way how to start and
stop virtual X server (framebuffer).

=head1 FUNCTIONS

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Files:
#
# /tmp/$Xid-pid - contains PID for X server we are running
# /tmp/$Xid-display - contains DISPLAY of our X server

. $BEAKERLIB/testing.sh
. $BEAKERLIB/infrastructure.sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtXGetCorrectID
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Generate internal ID from provided unique string, used by other
# rlVirtX* functions. You probably do not need to call this
# function and can forget about its existence.
#
# usage: rlVirtXGetCorrectID some_unique_string
#
#  * some_unique_string: unique identifier, you can use e.g. $TEST
#    (non-alnum chars will be stripped)

function rlVirtXGetCorrectID() {
  echo "$1" | sed "s/[^[:alnum:]]//g"
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtXGetPid
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Return PID of virtual X server
#
# usage: rlVirtXGetPid string
#
#  * string: ID (e.g. $TEST variable can be used)

function rlVirtXGetPid() {
  local Xid=$( rlVirtXGetCorrectID "$1" )
  if [ -f "/tmp/$Xid-pid" ]; then
    #rlLogDebug "rlVirtXGetPid: PID in '/tmp/$Xid-pid' is '$(cat /tmp/$Xid-pid)'"
    cat "/tmp/$Xid-pid"
  else
    #rlLogDebug "rlVirtXGetPid: PID file '/tmp/$Xid-pid' not accessible"
    return 1
  fi
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtXStartDisplay
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Start a virtual X server on display "display"
#
# usage: rlVirtXStartDisplay string display
#
#  * string: ID (e.g. $TEST variable can be used)
#  * display: DISPLAY number (without ':')

function rlVirtXStartDisplay() {
  local Xid=$( rlVirtXGetCorrectID "$1" )
  local Xdisplay=$( echo $2 | sed "s/[^0-9]//g" )
  rlLogDebug "rlVirtXStartDisplay: Starting a virtual X ($Xid) server on :$Xdisplay"
  #if [ -r "/tmp/.X$Xdisplay-lock" ]; then
  #  kill $( cat "/tmp/.X$Xdisplay-lock" ) &>/dev/null
  #  kill -9 $( cat "/tmp/.X$Xdisplay-lock" ) &>/dev/null
  #  rm -f "/tmp/.X$Xdisplay-lock"
  #  sleep 1
  #fi
  Xvfb :$Xdisplay -ac -screen 0 1600x1200x24 -fbdir /tmp &
  local Xpid=$!
  sleep 3
  if ! ps | grep $Xpid >/dev/null; then
    rlLogDebug "rlVirtXStartDisplay: Virtual X failed to start"
    return 1
  else
    rlLogDebug "rlVirtXStartDisplay: Started with PID '$Xpid' on display :$Xdisplay"
    echo "$Xpid" > /tmp/$Xid-pid
    echo ":$Xdisplay" > /tmp/$Xid-display
    return 0
  fi
}



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Virtual X Server --- Public Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Virtual X Server

Functions providing simple way how to start and stop virtual X
server.

WARNING: This BeakerLib component is still in development, use
carefully. If you encounter any problems contact jhutar@redhat.com.

=cut

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtualXStart
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

: <<=cut
=pod

=head3 rlVirtualXStart

Start a virtual X server on a first free display. Tries only first
N displays, so you can run out of them.

    rlVirtualXStart name

=over

=item name

String identifying the X server.

=back

Returns 0 when the server is started successfully.

=cut

function rlVirtualXStart() {
  local Xmax=3
  local Xid=$( rlVirtXGetCorrectID "$1" )
  local Xdisplay=0
  for Xdisplay in $( seq 1 $Xmax ); do
    rlLogDebug "rlVirtualXStart: Trying to start on display :$Xdisplay"
    if rlVirtXStartDisplay $Xid $Xdisplay; then
      rlLogDebug "rlVirtualXStart: Started on display :$Xdisplay"
      return 0
    fi
  done
  rlLogDebug "rlVirtualXStart: Was not able to start on displays from :1 to :Xmax"
  return 1
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtualXGetDisplay
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlVirtualXGetDisplay

Get the DISPLAY variable for specified virtual X server.

    rlVirtualXGetDisplay name

=over

=item name

String identifying the X server.

=back

Displays the number of display where specified virtual X server is
running to standard output. Returns 0 on success.

=cut

function rlVirtualXGetDisplay() {
  local Xid=$( rlVirtXGetCorrectID "$1" )
  if [ -f "/tmp/$Xid-display" ]; then
    #rlLogDebug "rlVirtualXGetDisplay: Display in '/tmp/$Xid-display' is '$(cat /tmp/$Xid-display)'"
    cat "/tmp/$Xid-display"
  else
    #rlLogDebug "rlVirtualXGetDisplay: Display file '/tmp/$Xid-display' not accessible"
    return 1
  fi
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlVirtualXStop
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlVirtualXStop

Kill the specified X server.

    rlVirtualXStop name

=over

=item name

String identifying the X server.

=back

Returns 0 when the server is stopped successfully.

=cut

function rlVirtualXStop() {
  local Xid=$( rlVirtXGetCorrectID "$1" )
  local Xpid=$( rlVirtXGetPid "$Xid" )
  local Xdisplay=$( rlVirtualXGetDisplay "$1" )
  if [ -z "$Xpid" ]; then
    rlLogDebug "rlVirtualXStop: Provide pid you want to kill"
    return 1
  fi
  if ps | grep $Xpid >/dev/null; then
    kill "$Xpid"
  fi
  sleep 2; # added by koca (some servers aren't so quick :))
  if ! ps | grep $Xpid >/dev/null; then
    rlLogDebug "rlVirtualXStop: Normal 'kill $Xpid' succeed"
  else
    rlLogWarning "rlVirtualXStop: I had to 'kill -9 $Xpid' (rc: $?) X server"
    kill -9 "$Xpid"
    sleep 1
    if [ -r "/tmp/.X$Xdisplay-lock" ]; then
      rlLogDebug "rlVirtualXStop: Lock file '/tmp/.X$Xdisplay-lock' still exists, last attempt"
      kill $( cat "/tmp/.X$Xdisplay-lock" ) &>/dev/null
      kill -9 $( cat "/tmp/.X$Xdisplay-lock" ) &>/dev/null
      rm -f "/tmp/.X$Xdisplay-lock"
      sleep 1
    fi
    if ps | grep $Xpid >/dev/null; then
      rlLogDebug "rlVirtualXStop: I was not able to kill pid '$Xpid', sorry"
      return 2
    fi
  fi
  rm -rf /tmp/$Xid-display /tmp/$Xid-pid
  sleep 1   # give it some time to end
  return 0
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Example
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<'=cut'
=pod

=head3 Example

Below is a simple example of usage. Note that a lot of usefull
debugging information is reported on the DEBUG level, so you can
run your test with C<DEBUG=1 make run> to get them.

    rlVirtualXStart $TEST
    rlAssert0 "Virtual X server started" $?
    export DISPLAY="$( rlVirtualXGetDisplay $TEST )"
    # ...your test which needs X...
    rlVirtualXStop $TEST
    rlAssert0 "Virtual X server killed" $?

These are "Requires" lines for your scripts - note different package
names for different RHEL versions:

    @echo "Requires: xorg-x11-server-Xvfb" >> $(METADATA) # RHEL-5
    @echo "Requires: xorg-x11-Xvfb"        >> $(METADATA) # RHEL-4
    @echo "Requires: XFree86-Xvfb"         >> $(METADATA) # RHEL-3

=cut


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# AUTHORS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head1 AUTHORS

=over

=item *

Jan Hutar <jhutar@redhat.com>

=item *

Petr Splichal <psplicha@redhat.com>

=back

=cut
