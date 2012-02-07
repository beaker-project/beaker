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

# XXX shouldn't hardcode this (comes from /distribution/beaker/add_systems)
export TEST_SYSTEM="virt-10"

if $(echo $SERVERS $STANDALONE | grep -q $HOSTNAME) ; then
    if [ -z "$SERVERS" ]; then
        SERVERS="$STANDALONE"
    fi
    # XXX should the setup task do this for us?
    rhts-run-simple-test $TEST/install-beaker-client "yum install -y beaker-client$VERSION"
    mkdir ~/.beaker_client
    cat >~/.beaker_client/config <<EOF
HUB_URL = "http://$SERVERS/bkr"
AUTH_METHOD = "password"
USERNAME = "admin"
PASSWORD = "testing"
EOF
    rhts-run-simple-test $TEST/custom-kickstart ./test_custom_kickstart.sh
    rhts-run-simple-test $TEST/no-custom-kickstart ./test_no_custom_kickstart.sh
else
    rhts-run-simple-test $TEST/noop true
fi
