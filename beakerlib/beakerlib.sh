#!/bin/bash
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

: <<'=cut'

=pod

=for comment beakerlib-manual-header

=head1 NAME

beakerlib.sh - BeakerLib Library main script

=head1 DESCRIPTION

The purpose of BeakerLib is to create a set of functions which would
make our life easier when writing tests and also to make our tests more
beautiful. Most important features which help to reach these goals are:

=over

=item

Basic set of functions for all common operations used in tests
(checking exit codes, mounting, handling rpms...)

=item

Uniform way of logging / submitting results thanks to journalling.

=item

The concept of phases (which pass/fail according to results of
asserts contained inside the phase).

=back

Main script sets C<BEAKERLIB> variable and sources other scripts
where the actual functions are defined. You should source it at
the beginning of your test with:

    . /usr/lib/beakerlib/beakerlib.sh

See the EXAMPLES section below for quick start.

=cut

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# beakerlib-manual-include
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:<<'=cut'

=pod

=for comment beakerlib-manual-footer

=head1 EXAMPLES

This is a minimal example of an BeakerLib test.

 # Include rhts and BeakerLib environment
 . /usr/bin/rhts-environment.sh
 . /usr/lib/beakerlib/beakerlib.sh

 rlJournalStart
     rlPhaseStartTest "Just making sure root hasn't run away"
         rlRun "grep ^root: /etc/passwd" 0 "Checking whether root is present"
     rlPhaseEnd
 rlJournalPrintText

Then next example is a bit more interesting real-life test which makes use of
journalling and phases to create the usual three-phase test structure: Setup,
Testing and Cleanup.

 # Include rhts and BeakerLib environment
 . /usr/bin/rhts-environment.sh
 . /usr/lib/beakerlib/beakerlib.sh

 PACKAGE=file

 rlJournalStart
     # prepare utf-16 encoded xml file
     rlPhaseStartSetup "Preparing UTF-16 encoded xml file"
         rlAssertRpm "file"
         rlRun 'XmlFile=`mktemp`'
         rlRun 'XmlFileUtf16=`mktemp`'
         rlRun "echo '<?xml version=\"1.0\"?> <foo> Hello world </foo>' >$XmlFile" \
             0 "Creating xml file"
         rlRun "xmllint --encode UTF-16 $XmlFile > $XmlFileUtf16" \
             0 "Converting to UTF-16 encoding"
     rlPhaseEnd

     # test file detection
     rlPhaseStartTest "Testing correct file detection"
         rlLog "file reports: `file -b $XmlFileUtf16`"
         rlRun "file $XmlFileUtf16 | grep -q 'XML document'" \
             0 "Checking whether xml file is correctly recognized"
     rlPhaseEnd

     # cleanup
     rlPhaseStartCleanup "Cleaning up"
         rlRun "rm $XmlFile $XmlFileUtf16" 0 "Removing xml files"
     rlPhaseEnd
 rlJournalPrintText

=head1 LINKS

=over

=item Quick Reference Guide

https://fedorahosted.org/beaker/wiki/BeakerLib/QuickReferenceGuide

=item Manual

https://fedorahosted.org/beaker/wiki/BeakerLib/Manual

=item Project Page

https://fedorahosted.org/beaker/wiki/BeakerLib

=item Bugs reporting

https://fedorahosted.org/beaker/newticket?keywords=BeakerLib&summary=BeakerLib:

=back

=head1 AUTHORS

=over

=item *

Petr Muller <pmuller@redhat.com>

=item *

Ondrej Hudlicky <ohudlick@redhat.com>

=item *

Jan Hutar <jhutar@redhat.com>

=item *

Petr Splichal <psplicha@redhat.com>

=item *

Ales Zelinka <azelinka@redhat.com>

=cut

if set -o | grep posix | grep on 
then
  set +o posix
  export POSIXFIXED="YES"
else
  export POSIXFIXED="NO"
fi

set -e
export BEAKERLIB=${BEAKERLIB:-"/usr/lib/beakerlib/"}
. $BEAKERLIB/infrastructure.sh
. $BEAKERLIB/journal.sh
. $BEAKERLIB/logging.sh
. $BEAKERLIB/rpms.sh
. $BEAKERLIB/testing.sh
. $BEAKERLIB/analyze.sh
. $BEAKERLIB/performance.sh
. $BEAKERLIB/virtualX.sh
if [ -d $BEAKERLIB/plugins/ ]
then
  for source in $BEAKERLIB/plugins/*.sh
  do
  . $source
  done
fi
set +e
