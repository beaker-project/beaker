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
# Author: Jan Hutar <jhutar@redhat.com>

# Remove the script
rm -f runtests-worker.sh

# Include header
echo "#!/bin/bash" >runtests-worker.sh

# Include set up section
cat >>runtests-worker.sh <<EOF
# We need to export the variables out of the oneTimeSetUp function
export BEAKERLIB=$PWD/'..'
export TEST='/CoreOS/distribution/beakerlib/unit-tests'
export OUTPUTFILE="$( mktemp )"
export RECIPEID='123'
export TESTID='123456'

#include usefull functions
. library.sh

#mock report_result
report_result(){
 true;
}

oneTimeSetUp() {
  # Source script we are going to test
  . ../beakerlib.sh
  set +u
  rlJournalStart
  return 0
}
EOF

# Include all test scripts
test_files=$@
[ -z "$test_files" ] && test_files=$( ls *Test.sh )
for file in $test_files; do
  echo "Including file '$file'"
  echo '#=================================================' >>runtests-worker.sh
  cat $file >>runtests-worker.sh
  echo '#=================================================' >>runtests-worker.sh
done

# Include shunit2
echo ". shunit2" >>runtests-worker.sh

# Run the tests
chmod +x runtests-worker.sh
log=$( mktemp )
./runtests-worker.sh 2>&1 | tee $log

# Get results out of the log
log_passed=$( tail -n 4 $log | grep "^tests passed" | sed "s/tests passed: \([0-9]\+\)$/\1/" )
log_failed=$( tail -n 4 $log | grep "^tests failed" | sed "s/tests failed: \([0-9]\+\)$/\1/" )
log_total=$(  tail -n 4 $log | grep "^tests total"  | sed "s/tests total:  \([0-9]\+\)$/\1/" )
[ $log_passed -eq $log_total ] && exit 0
exit 1
