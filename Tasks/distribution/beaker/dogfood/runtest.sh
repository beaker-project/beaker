#!/bin/sh

# Copyright (c) 2010 Red Hat, Inc. All rights reserved. This copyrighted material 
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
# Author: Dan Callaghan <dcallagh@redhat.com>

rhts-run-simple-test $TEST/beakerd_stop "/sbin/service beakerd stop"
if [[ "$SOURCE" == "git" ]] ; then
    rhts-run-simple-test $TEST/yum_install_git "yum install -y /tmp/tito/noarch/beaker-integration-tests-*.rpm"
else
    rhts-run-simple-test $TEST/yum_install "yum install -y beaker-integration-tests$VERSION"
fi
rhts-run-simple-test $TEST/update_config "./update-config.sh"
rhts-run-simple-test $TEST/httpd_reload "/sbin/service httpd reload"

if echo $SERVERS | grep -q $HOSTNAME ; then
    echo "Running with remote lab controller: ${CLIENTS}"
    export BEAKER_LABCONTROLLER_HOSTNAME="${CLIENTS}"
else
    echo "Running in single-host mode"
    export BEAKER_LABCONTROLLER_HOSTNAME="${HOSTNAME}"
fi
rhts-run-simple-test $TEST "nosetests -v $NOSEARGS" || :
rhts-submit-log -l /var/log/beaker/server-errors.log
