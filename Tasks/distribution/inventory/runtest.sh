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
# Author: Bill Peck, Gurhan Ozen

modprobe kvm
modprobe kvm_amd
modprobe kvm_intel

if [ -z "$HOSTNAME" ]; then
    hostname=$(hostname)
else
    hostname=$HOSTNAME
fi

# Push to Inventory server
if [ -z "$server" ]; then
    server="http://$LAB_CONTROLLER:8000/server"
fi
rhts-run-simple-test $TEST "./push-inventory.py --server $server -h $hostname"
rhts-run-simple-test $TEST "./pushInventory.py --server $server -h $hostname"
