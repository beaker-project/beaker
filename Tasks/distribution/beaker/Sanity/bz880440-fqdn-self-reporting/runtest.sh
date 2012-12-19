#!/bin/bash
# vim: dict=/usr/share/beakerlib/dictionary.vim cpt=.,w,b,u,t,i,k
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   runtest.sh of /tools/ncoghlan/Sanity/bz880440-fqdn-self-reporting
#   Description: Check output of hostname command
#   Author: Nick Coghlan <ncoghlan@redhat.com>
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
#   Copyright (c) 2012 Red Hat, Inc. All rights reserved.
#
#   This copyrighted material is made available to anyone wishing
#   to use, modify, copy, or redistribute it subject to the terms
#   and conditions of the GNU General Public License version 2.
#
#   This program is distributed in the hope that it will be
#   useful, but WITHOUT ANY WARRANTY; without even the implied
#   warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#   PURPOSE. See the GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public
#   License along with this program; if not, write to the Free
#   Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
#   Boston, MA 02110-1301, USA.
#
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Include Beaker environment
. /usr/bin/rhts-environment.sh || exit 1
. /usr/share/beakerlib/beakerlib.sh || exit 1


# Make sure to include the following in each recipe definition:
# <ks_appends>
#   <ks_append>
# %post
# hostname -f > /tmp/bz880440_ks_post_FQDN.txt
# hostname -i > /tmp/bz880440_ks_post_IP.txt
# echo $HOSTNAME > /tmp/bz880440_ks_post_HOSTNAME.txt
# tail -n1 /etc/hosts | sed 's/[^[:space:]]*[[:space:]]*\([^[:space:]]*\).*/\1/' > /tmp/bz880440_ks_post_parsed_host.txt
# grep ^HOSTNAME= /etc/sysconfig/network | cut -f2- -d= > /tmp/bz880440_ks_post_sysconfig_network.txt
# cp /etc/hostname /tmp/bz880440_ks_post_etc_hostname.txt
# cp /etc/hosts /tmp/bz880440_ks_post_etc_hosts.txt
# cp /tmp/bz880440_ks_post_FQDN.txt /tmp/bz880440_ks_post_corrected_FQDN.txt
# if [[ -z "$KS_POST_FQDN" || $KS_POST_FQDN == localhost || $KS_POST_FQDN == localhost.* ]] ; then
#     if [ -f /etc/hostname ] ; then
#         cp /tmp/bz880440_ks_post_etc_hostname.txt /tmp/bz880440_ks_post_corrected_FQDN.txt
#     elif grep -q ^HOSTNAME= /etc/sysconfig/network ; then
#         cp /tmp/bz880440_ks_post_sysconfig_network.txt /tmp/bz880440_ks_post_corrected_FQDN.txt
#     fi
# fi
#   </ks_append>
# </ks_appends>


rlJournalStart
    rlPhaseStartSetup
        rlRun "TmpDir=\$(mktemp -d)" 0 "Creating tmp directory"
        rlRun "pushd $TmpDir"
    rlPhaseEnd

    rlPhaseStartTest
        rlAssertExists /tmp/bz880440_ks_post_FQDN.txt
        rlFileSubmit /tmp/bz880440_ks_post_FQDN.txt
        rlAssertExists /tmp/bz880440_ks_post_IP.txt
        rlFileSubmit /tmp/bz880440_ks_post_IP.txt
        rlAssertExists /tmp/bz880440_ks_post_HOSTNAME.txt
        rlFileSubmit /tmp/bz880440_ks_post_HOSTNAME.txt
        rlAssertExists /tmp/bz880440_ks_post_etc_hosts.txt
        rlFileSubmit /tmp/bz880440_ks_post_etc_hosts.txt
        if [ -f /etc/hostname ] ; then
            rlAssertExists /tmp/bz880440_ks_post_etc_hostname.txt
            rlFileSubmit /tmp/bz880440_ks_post_etc_hostname.txt
        fi
        rlAssertExists /tmp/bz880440_ks_post_parsed_host.txt
        rlFileSubmit /tmp/bz880440_ks_post_parsed_host.txt
        rlAssertExists /tmp/bz880440_ks_post_sysconfig_network.txt
        rlFileSubmit /tmp/bz880440_ks_post_sysconfig_network.txt
        rlAssertExists /tmp/bz880440_ks_post_corrected_FQDN.txt
        rlFileSubmit /tmp/bz880440_ks_post_corrected_FQDN.txt
        rlRun "REPORTED_FQDN=\$(hostname -f)" 0 "Get FQDN"
        rlLog "Self-reported FQDN: $REPORTED_FQDN"
        rlRun "KS_POST_FQDN=\$(cat /tmp/bz880440_ks_post_FQDN.txt)" 0 "Get FQDN from kickstart post"
        rlLog "Self-reported FQDN from kickstart post: $KS_POST_FQDN"
        # This next if statement should match the logic in the rhts_post if statement
        if [[ -z "$KS_POST_FQDN" || $KS_POST_FQDN == localhost || $KS_POST_FQDN == localhost.* ]] ; then
            # hostname -f is the most future-proof approach, but it isn't always reliable
            rlLog "Dubious self-reported FQDN detected, attempting to correct it"
            if [ -f /etc/hostname ] ; then
                # Preferred fallback if the OS is recent enough to provide it
                rlRun "KS_POST_FQDN=\$(cat /tmp/bz880440_ks_post_etc_hostname.txt)" 0 "Read /etc/hostname from kickstart post"
                rlLog "Corrected self-reported FQDN from kickstart post: $KS_POST_FQDN"
            elif grep -q ^HOSTNAME= /etc/sysconfig/network ; then
                # Last resort fallback to try to report something sensible
                rlRun "KS_POST_FQDN=\$(cat /tmp/bz880440_ks_post_sysconfig_network.txt)" 0 "Read /etc/sysconfig/network from kickstart post"
                rlLog "Corrected self-reported FQDN from kickstart post: $KS_POST_FQDN"
            else
                rlFail "No fallback available to correct self-reported FQDN"
            fi
        fi
        rlRun "REPORTED_IP=\$(hostname -i)" 0 "Get IP address"
        rlLog "Self-reported IP address: $REPORTED_IP"
        rlRun "KS_POST_IP=\$(cat /tmp/bz880440_ks_post_IP.txt)" 0 "Get IP address from kickstart post"
        rlLog "Self-reported IP address from kickstart post: $KS_POST_IP"
        rlLog "Self-reported HOSTNAME: $HOSTNAME"
        rlLog "Self-reported HOSTNAME from kickstart post: $(cat /tmp/bz880440_ks_post_HOSTNAME.txt)"
        rlFileSubmit /etc/hosts
# Alas, hostname doesn't support "--all-fqdns" until RHEL 6 :(
#        rlRun "REPORTED_FQDN_ALL=\$(hostname --all-fqdns)" 0 "Get all FQDNs"
#        rlLog "All reported FQDNs: $REPORTED_FQDN_ALL"
        rlAssertNotEquals "Check current FQDN is not empty" "x_$REPORTED_FQDN" "x_"
        rlAssertNotEquals "Check current FQDN is not 'localhost'" "$REPORTED_FQDN" "localhost"
        rlAssertNotEquals "Check current FQDN is not 'localhost.localdomain'" "$REPORTED_FQDN" "localhost.localdomain"
        rlAssertEquals "Check FQDN self-report from kickstart post" "$KS_POST_FQDN" "$REPORTED_FQDN"
        KS_POST_SNIPPET_FQDN=$(cat /tmp/bz880440_ks_post_corrected_FQDN.txt)
        rlAssertEquals "Check fallback logic in recipe snippets" "$KS_POST_SNIPPET_FQDN" "$REPORTED_FQDN"
    rlPhaseEnd

    rlPhaseStartCleanup
        rlRun "popd"
        rlRun "rm -r $TmpDir" 0 "Removing tmp directory"
    rlPhaseEnd
rlJournalPrintText
rlJournalEnd
