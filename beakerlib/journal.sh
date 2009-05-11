#!/bin/sh

# journal.sh - part of BeakerLib
# Authors: 	Petr Muller     <pmuller@redhat.com> 
#
# Description: BeakerLib journalling functions
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

journal.sh - BeakerLib journalling functions

=head1 DESCRIPTION

Routines for initializing the journalling features and pretty
printing journal contents.

=head1 FUNCTIONS

=cut

__INTERNAL_JOURNALIST=$BEAKERLIB/python/journalling.py


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlJournalStart
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Journalling

=head3 rlJournalStart

Initialize the journal file.

    rlJournalStart

Run on the very beginning of your script to initialize journalling
functionality.

=cut

rlJournalStart(){
	local TID=${TESTID:-"debugging"}
	local PKG=${PACKAGE:-"debugging"}
	$__INTERNAL_JOURNALIST init --id "$TID" --test "$TEST" --package "$PKG"
}

# backward compatibility
rlStartJournal() {
    rlJournalStart
    rlLogWarning "rlStartJournal is obsoleted by rlJournalStart"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlJournalEnd
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head2 Journalling

=head3 rlJournalEnd

Summarizes the test run and uploads the journal file

    rlJournalEnd

Run on the very end of your script to print summary of the whole test run,
generate OUTPUTFILE and include journal in Beaker logs.

=cut

rlJournalEnd(){
    rlJournalPrintText > $OUTPUTFILE
    local JOURNAL=`mktemp -d`/journal.xml
    rlJournalPrint raw > $JOURNAL

    if [ -n "$TESTID" ] ; then
        rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $JOURNAL \
        || rlLogError "rlJournalEnd: Submit wasn't successful"
    else
        rlLog "JOURNAL: $JOURNAL"
        rlLog "OUTPUTFILE: $OUTPUTFILE"
    fi

}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlJournalPrint
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<'=cut'
=pod

=head3 rlJournalPrint

Prints the content of the journal in pretty xml format.

    rlJournalPrint [type]

=item type
Can be either 'raw' or 'pretty', with the latter as a default.
Raw: xml is in raw form, no indentation etc
Pretty: xml is pretty printed, indented, with one record per line

Example:

 <?xml version="1.0" ?>
 <RHTS_TEST>
     <test_id>
         debugging
     </test_id>
     <package>
         file
     </package>
     <testname>
         /CoreOS/file/Regression/bz235420-little-endian-xml-file
     </testname>
     <release>
         Red Hat Enterprise Linux Server release 5.2 (Tikanga)
     </release>
     <purpose>
         Test Name: bz235420-little-endian-xml-file - Bugzilla(s) 235420
 Author: Petr Splichal &lt;psplicha@redhat.com&gt;
 Location: /CoreOS/file/Regression/bz235420-little-endian-xml-file

 Short Description: Little endian xml file detection.


 Long Description:
 
 Check whether UTF-16, little-endian encoded XML file is well recognized by file.

     </purpose>
     <log>
         <phase name="Preparing UTF-16 encoded xml file" result="PASS" score="0" type="ABORT">
             <test message="Checking for the presence of file rpm">
                 PASS
             </test>
             <message severity="LOG">
                 file RPM version: 4.17-15
             </message>
             <test message="Running \'XmlFile=`mktemp`\' and expecting 0">
                 PASS
             </test>
             <test message="Running \'XmlFileUtf16=`mktemp`\' and expecting 0">
                 PASS
             </test>
             <test message="Creating xml file">
                 PASS
             </test>
             <test message="Converting to UTF-16 encoding">
                 PASS
             </test>
         </phase>
         <phase name="Testing correct file detection" result="PASS" score="0" type="FAIL">
             <message severity="LOG">
                 file reports: XML document text (little endian with byte order mark)
             </message>
             <test message="Checking whether xml file is correctly recognized">
                 PASS
             </test>
         </phase>
         <phase name="Cleaning up" result="PASS" score="0" type="WARN">
             <test message="Removing xml files">
                 PASS
             </test>
         </phase>
     </log>
 </RHTS_TEST>

=cut

rlJournalPrint(){
	local TID=${TESTID:-"debugging"}
  local TYPE=${1:-"pretty"}
	$__INTERNAL_JOURNALIST dump --id $TID --type "$TYPE"
}

# backward compatibility
rlPrintJournal() {
    rlLogWarning "rlPrintJournal is obsoleted by rlJournalPrint"
    rlJournalPrint
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# rlJournalPrintText
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
: <<=cut
=pod

=head3 rlJournalPrintText

Prints the content of the journal in pretty text format.

    rlJournalPrintText

Example:

 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 :: [   LOG    ] :: TEST PROTOCOL
 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

 :: [   LOG    ] :: Test run ID: debugging
 :: [   LOG    ] :: Package    : file
 :: [   LOG    ] :: Test name  : /CoreOS/file/Regression/bz235420-little-endian-xml-file
 :: [   LOG    ] :: Distro:    : Red Hat Enterprise Linux Server release 5.2 (Tikanga)

 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 :: [   LOG    ] :: Test description
 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

 Test Name: bz235420-little-endian-xml-file - Bugzilla(s) 235420
 Author: Petr Splichal <psplicha@redhat.com>
 Location: /CoreOS/file/Regression/bz235420-little-endian-xml-file

 Short Description: Little endian xml file detection.
 
 
 Long Description:

 Check whether UTF-16, little-endian encoded XML file is well recognized by file.


 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 :: [   LOG    ] :: Preparing UTF-16 encoded xml file
 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

 :: [   PASS   ] :: Checking for the presence of file rpm
 :: [   LOG    ] :: file RPM version: 4.17-15
 :: [   PASS   ] :: Running \'XmlFile=`mktemp`\' and expecting 0
 :: [   PASS   ] :: Running \'XmlFileUtf16=`mktemp`\' and expecting 0
 :: [   PASS   ] :: Creating xml file
 :: [   PASS   ] :: Converting to UTF-16 encoding
 :: [   LOG    ] :: ASSERTIONS: 5 PASS, 0 FAIL

 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 :: [   LOG    ] :: Testing correct file detection
 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

 :: [   LOG    ] :: file reports: XML document text (little endian with byte order mark)
 :: [   PASS   ] :: Checking whether xml file is correctly recognized
 :: [   LOG    ] :: ASSERTIONS: 1 PASS, 0 FAIL

 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
 :: [   LOG    ] :: Cleaning up
 ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::

 :: [   PASS   ] :: Removing xml files
 :: [   LOG    ] :: ASSERTIONS: 1 PASS, 0 FAIL

=cut

rlJournalPrintText(){
  local TID=${TESTID:-"debugging"}
  local SEVERITY=${LOG_LEVEL:-"WARNING"}
  [ "$DEBUG" == 'true' -o "$DEBUG" == '1' ] && SEVERITY="DEBUG"
  $__INTERNAL_JOURNALIST printlog --id $TID --severity $SEVERITY
}

# backward compatibility
rlCreateLogFromJournal(){
    rlLogWarning "rlCreateLogFromJournal is obsoleted by rlJournalPrintText"
    rlJournalPrintText
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Internal Stuff
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

rljAddPhase(){
	local TID=${TESTID:-"debugging"}
	local MSG=${2:-"Phase of $1 type"}
	rlLogDebug "rljAddPhase: Phase $MSG started"
	$__INTERNAL_JOURNALIST addphase --id $TID --name "$MSG" --type "$1"
} 

rljClosePhase(){
	local TID=${TESTID:-"debugging"}
	local out=`$__INTERNAL_JOURNALIST finphase --id $TID`
	local score=$?
	local logfile=`mktemp`
	local result="`echo $out | cut -d ':' -f 2`"
	local name=`echo $out | cut -d ':' -f 3 | sed 's/[^[:alnum:]]\+/-/g'`
	rlLogDebug "rljClosePhase: Phase $name closed"
	rlJournalPrintText > $logfile
	rlReport "$TEST/$name" "$result" "$score" "$logfile"
}

rljAddTest(){
	local TID=${TESTID:-"debugging"}
	$__INTERNAL_JOURNALIST test --id $TID --message "$1" --result "$2"
}

rljAddMetric(){
	local TID=${TESTID:-"debugging"}
	local MID="$2"
	local VALUE="$3"
	local TOLERANCE=${4:-"0.2"}
	if [ "$MID" == "" ] || [ "$VALUE" == "" ]
	then
		rlLogError "TEST BUG: Bad call of rlLogMetric"
		return 1
	fi
	rlLogDebug "rljAddMetric: Storing metric $MID with value $VALUE and tolerance $TOLERANCE"
	$__INTERNAL_JOURNALIST metric --id $TID --type $1 --name "$MID" --value "$VALUE" --tolerance "$TOLERANCE"
	return $?
}

rljAddMessage(){
	local TID=${TESTID:-"debugging"}
	$__INTERNAL_JOURNALIST log --id $TID --message "$1" --severity "$2"
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
