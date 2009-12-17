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
# Author: Alexander Todorov <atodorov@redhat.com>

# source the test script helpers
. /usr/bin/rhts-environment.sh


echo "--- start of runtest.sh ---" | tee -a $OUTPUTFILE

echo "INFO: additional parameters will be inm the form TEST_PARAM_NAME=value" | tee -a $OUTPUTFILE

echo "--- start environment ---" | tee -a $OUTPUTFILE
set | tee -a $OUTPUTFILE
echo "--- --- --- --- ---" | tee -a $OUTPUTFILE
export | tee -a $OUTPUTFILE
echo "--- end environment ---" | tee -a $OUTPUTFILE

report_result $TEST PASS

echo "--- end of runtest.sh ---" | tee -a $OUTPUTFILE
