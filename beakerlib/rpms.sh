#!/bin/bash

# rpms.sh - part of BeakerLib
# Authors: 	Petr Muller     <pmuller@redhat.com> 
#
# Description: Contains helpers for RPM manipulation
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

rpms.sh - BeakerLib functions for RPM manipulation

=head1 DESCRIPTION

Functions in this BeakerLib script are used for RPM manipulation.

=head1 FUNCTIONS

=cut

. $BEAKERLIB/testing.sh
. $BEAKERLIB/infrastructure.sh

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__INTERNAL_RpmPresent() {
	local assert=$1
	local name=$2
	local version=$3
	local release=$4
	local arch=$5

	local package=$name-$version-$release.$arch
	[ "$arch"    == "" ] && package=$name-$version-$release
	[ "$release" == "" ] && package=$name-$version
	[ "$version" == "" ] && package=$name

        if [ -n "$package" ]; then
		rpm -q $package
		local status=$?
	else
		local status=100
	fi

	if [ "$assert" == "assert" ] ; then
		__INTERNAL_ConditionalAssert "Checking for the presence of $package rpm" $status
	elif [ "$assert" == "assert_inverted" ] ; then
		if [ $status -eq 1 ]; then
			status=0
                        echo "Status was 1 now 0 '$package'" >>/tmp/aaa
		elif [ $status -eq 0 ]; then
			status=1
                        echo "Status was 0 now 1 '$package'" >>/tmp/aaa
		fi
		__INTERNAL_ConditionalAssert "Checking for the non-presence of $package rpm" $status
	elif [ $status -eq 0 ] ; then
		rlLog "Package $package is present"
	else
		rlLog "Package $package is not present"
	fi

	return $status
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlCheckRpm
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Rpm Handling

=head3 rlCheckRpm

Check whether a package is installed.

    rlCheckRpm name [version] [release] [arch]

=over

=item name

Package name like C<kernel>

=item version

Package version like C<2.6.25.6>

=item release

Package release like C<55.fc9>

=item arch

Package architucture like C<i386>

=back

Returns 0 if the specified package is installed.

=cut

rlCheckRpm(){
  __INTERNAL_RpmPresent noassert $1 $2 $3 $4
}

# backward compatibility
rlRpmPresent(){
  rlLogWarning "rlRpmPresent is obsoleted by rlCheckRpm"
  __INTERNAL_RpmPresent noassert $1 $2 $3 $4
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertRpm
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertRpm

Assertion making sure that a package is installed.

    rlAssertRpm name [version] [release] [arch]>

=over

=item name

Package name like C<kernel>

=item version

Package version like C<2.6.25.6>

=item release

Package release like C<55.fc9>

=item arch

Package architucture like C<i386>

=back

Returns 0 and asserts PASS if the specified package is installed.

=cut

rlAssertRpm(){	
  __INTERNAL_RpmPresent assert $1 $2 $3 $4
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlAssertNotRpm
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlAssertNotRpm

Assertion making sure that a package is not installed. This is
just inverse of C<rlAssertRpm>.

    rlAssertNotRpm name [version] [release] [arch]>

=over

=item name

Package name like C<kernel>

=item version

Package version like C<2.6.25.6>

=item release

Package release like C<55.fc9>

=item arch

Package architucture like C<i386>

=back

Returns 0 and asserts PASS if the specified package is not installed.

=head3 Example

Function C<rlAssertRpm> is useful especially in prepare phase
where it causes abort if a package is missing, while
C<rlCheckRpm> is handy when doing something like:

    if ! rlCheckRpm package; then
         yum install package
         rlAssertRpm package
    fi

=cut

rlAssertNotRpm(){
   __INTERNAL_RpmPresent assert_inverted $1 $2 $3 $4
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

Petr Splichal <psplicha@redhat.com>

=item *

Ales Zelinka <azelinka@redhat.com>

=back

=cut
