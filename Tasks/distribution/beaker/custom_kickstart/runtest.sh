#!/bin/bash

# Copyright (c) 2012 Red Hat, Inc. All rights reserved. This copyrighted material 
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

set -ex

# XXX shouldn't hardcode this (comes from /distribution/beaker/add_systems)
SYSTEM="virt-10"

function test_custom_kickstart() {
    bkr job-submit - <<EOF
<job retention_tag="scratch">
    <whiteboard>
        custom kickstart
    </whiteboard>
    <recipeSet>
        <recipe>
            <distroRequires>
                <and>
                    <distro_arch op="=" value="x86_64"/>
                    <distro_family op="=" value="RedHatEnterpriseLinux6"/>
                    <distro_variant op="=" value="Server"/>
                </and>
            </distroRequires>
            <hostRequires>
                <hostname op="=" value="$SYSTEM" />
            </hostRequires>
            <task name="/distribution/install" role="STANDALONE">
                <params/>
            </task>
            <kickstart>
<![CDATA[
install
firewall --disabled
rootpw --iscrypted $1$lol$HhoQLlgGBmDdhd0l7YaK2.
text
keyboard us
lang en_AU
selinux --permissive
skipx
logging --level=info
timezone --utc Australia/Brisbane
bootloader --location=mbr
zerombr
clearpart --all --initlabel
autopart
reboot

%packages --nobase
@core

%post --log=/dev/console
echo hello
%end
]]>
            </kickstart>
        </recipe>
    </recipeSet>
</job>
EOF

    # XXX find a better way to wait for the job to start
    sleep 90

    wget -nv -O kickstart.actual "http://$SERVERS/cblr/svc/op/ks/system/$SYSTEM"
    rhts-submit-log -l kickstart.actual
    # We could diff this against an expected kickstart, like this...
    #diff -u kickstart.expected kickstart.actual
    # We would get an exit status of 1 if there were some difference.
    # But the kickstart has lots of site-specific stuff in it (distro paths etc)
    # so that's not really practical. :-(
    # We can at least check for our magical %post command:
    grep -q '^echo hello$' kickstart.actual

    echo PASSED
}

if $(echo $SERVERS $STANDALONE | grep -q $HOSTNAME) ; then
    if [ -z "$SERVERS" ]; then
        SERVERS="$STANDALONE"
    fi
    # XXX should the setup task do this for us?
    yum install -y "beaker-client$VERSION"
    mkdir ~/.beaker_client
    cat >~/.beaker_client/config <<EOF
HUB_URL = "http://$SERVERS/bkr"
AUTH_METHOD = "password"
USERNAME = "admin"
PASSWORD = "testing"
EOF
    test_custom_kickstart
else
    rhts-run-simple-test $TEST/noop true
fi
