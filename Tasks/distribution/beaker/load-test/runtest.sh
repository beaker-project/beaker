#!/bin/sh

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
#
# Author: Raymond Mancy <rmancy@redhat.com>

function ClientCfg()
{
    cat << __EOF__ > /etc/beaker/client.conf
HUB_URL = "https://$BEAKER_LOAD_SERVER/"
AUTH_METHOD = "password"
USERNAME = "admin"
PASSWORD = "testing"
MSG_BUS = False
__EOF__
}

ClientCfg
rhts-run-simple-test $TEST "funnel --profile load.xml --graphite-server $GRAPHITE_SERVER --load-server $BEAKER_LOAD_SERVER"
