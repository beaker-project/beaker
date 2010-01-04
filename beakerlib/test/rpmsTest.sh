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

test_rlAssertRpm() {
  local first=$( rpm -qa --qf "%{NAME}.%{ARCH}\n" | tail -n 1 )
  local first_n=$( rpm -q $first --qf "%{NAME}\n" | tail -n 1 )
  local first_v=$( rpm -q $first --qf "%{VERSION}\n" | tail -n 1 )
  local first_r=$( rpm -q $first --qf "%{RELEASE}\n" | tail -n 1 )
  local first_a=$( rpm -q $first --qf "%{ARCH}\n" | tail -n 1 )
  rlJournalStart

  assertTrue "rlAssertRpm returns 0 on installed 'N' package" \
    "rlAssertRpm $first_n"
  assertTrue "rlAssertRpm returns 0 on installed 'NV' package" \
    "rlAssertRpm $first_n $first_v"
  assertTrue "rlAssertRpm returns 0 on installed 'NVR' package" \
    "rlAssertRpm $first_n $first_v $first_r"
  assertTrue "rlAssertRpm returns 0 on installed 'NVRA' package" \
    "rlAssertRpm $first_n $first_v $first_r $first_a"

  assertFalse "rlAssertRpm returns non-0 when invoked without parameters" \
    "rlAssertRpm"

  assertFalse "rlAssertRpm returns non-0 on not-installed 'N' package" \
    "rlAssertRpm $first_n-not-installed-package"
  assertFalse "rlAssertRpm returns non-0 on not-installed 'NV' package" \
    "rlAssertRpm $first_n $first_v.1.2.3"
  assertFalse "rlAssertRpm returns non-0 on not-installed 'NVR' package" \
    "rlAssertRpm $first_n $first_v $first_r.1.2.3"
  assertFalse "rlAssertRpm returns non-0 on not-installed 'NVRA' package" \
    "rlAssertRpm $first_n $first_v $first_r ${first_a}xyz"

  assertTrue "rlAssertRpm increases SCORE when package is not found" \
    "rlPhaseStart FAIL rpm-asserts; rlAssertRpm ahsgqyrg ; rlPhaseEnd ;rlJournalPrintText |
	 tail -2| head -n 1 | grep -q '1 bad' "
}

test_rlAssertNotRpm() {
  local first=$( rpm -qa --qf "%{NAME}.%{ARCH}\n" | tail -n 1 )
  local first_n=$( rpm -q $first --qf "%{NAME}\n" | tail -n 1 )
  local first_v=$( rpm -q $first --qf "%{VERSION}\n" | tail -n 1 )
  local first_r=$( rpm -q $first --qf "%{RELEASE}\n" | tail -n 1 )
  local first_a=$( rpm -q $first --qf "%{ARCH}\n" | tail -n 1 )

  assertFalse "rlAssertNotRpm returns non-0 on installed 'N' package" \
    "rlAssertNotRpm $first_n"
  assertFalse "rlAssertNotRpm returns non-0 on installed 'NV' package" \
    "rlAssertNotRpm $first_n $first_v"
  assertFalse "rlAssertNotRpm returns non-0 on installed 'NVR' package" \
    "rlAssertNotRpm $first_n $first_v $first_r"
  assertFalse "rlAssertNotRpm returns non-0 on installed 'NVRA' package" \
    "rlAssertNotRpm $first_n $first_v $first_r $first_a"

  assertFalse "rlAssertNotRpm returns non-0 when run without parameters" \
    "rlAssertNotRpm"

  assertTrue "rlAssertNotRpm returns 0 on not-installed 'N' package" \
    "rlAssertNotRpm $first_n-not-installed-package"
  assertTrue "rlAssertNotRpm returns 0 on not-installed 'NV' package" \
    "rlAssertNotRpm $first_n $first_v.1.2.3"
  assertTrue "rlAssertNotRpm returns 0 on not-installed 'NVR' package" \
    "rlAssertNotRpm $first_n $first_v $first_r.1.2.3"
  assertTrue "rlAssertNotRpm returns 0 on not-installed 'NVRA' package" \
    "rlAssertNotRpm $first_n $first_v $first_r ${first_a}xyz"

  assertTrue "rlAssertNotRpm increases SCORE when package is found" \
  "rlPhaseStart FAIL rpm-not-asserts; rlAssertNotRpm $first_n ; rlPhaseEnd ;rlJournalPrintText |
	 tail -2| head -1 | grep -q '1 bad' "

  assertTrue "rlAssertNotRpm increases SCORE when package is found" \
  "rlPhaseStart FAIL rpm-not-asserts; rlAssertNotRpm $first_n ; rlPhaseEnd ;rlCreateLogFromJournal |
	 tail -2| head -1 | grep -q '1 bad' "
}

test_rlCheckRpm() {
  local first=$( rpm -qa --qf "%{NAME}.%{ARCH}\n" | tail -n 1 )
  local first_n=$( rpm -q $first --qf "%{NAME}\n" | tail -n 1 )
  local first_v=$( rpm -q $first --qf "%{VERSION}\n" | tail -n 1 )
  local first_r=$( rpm -q $first --qf "%{RELEASE}\n" | tail -n 1 )
  local first_a=$( rpm -q $first --qf "%{ARCH}\n" | tail -n 1 )

  : > $OUTPUTFILE
  assertTrue "rlRpmPresent returns 0 on installed 'N' package" \
    "rlRpmPresent $first_n"
  assertTrue "rlRpmPresent returns 0 on installed 'NV' package" \
    "rlRpmPresent $first_n $first_v"
  assertTrue "rlRpmPresent returns 0 on installed 'NVR' package" \
    "rlRpmPresent $first_n $first_v $first_r"
  assertTrue "rlRpmPresent returns 0 on installed 'NVRA' package" \
    "rlRpmPresent $first_n $first_v $first_r $first_a"
  __checkLoggedText $first_n $OUTPUTFILE

  assertFalse "rlRpmPresent returns non-0 when run without parameters" \
    "rlRpmPresent"

  : > $OUTPUTFILE
  assertFalse "rlRpmPresent returns non-0 on not-installed 'N' package" \
    "rlRpmPresent $first_n-not-installed-package"
  assertFalse "rlRpmPresent returns non-0 on not-installed 'NV' package" \
    "rlRpmPresent $first_n $first_v.1.2.3"
  assertFalse "rlRpmPresent returns non-0 on not-installed 'NVR' package" \
    "rlRpmPresent $first_n $first_v $first_r.1.2.3"
  assertFalse "rlRpmPresent returns non-0 on not-installed 'NVRA' package" \
    "rlRpmPresent $first_n $first_v $first_r ${first_a}xyz"
  __checkLoggedText $first_n $OUTPUTFILE

  assertTrue "rlRpmPresent doesn't increase SCORE when package is not found" \
    "rlPhaseStart FAIL rpm-present; rlRpmPresent ahsgqyrg ; rlPhaseEnd ;rlJournalPrintText |
	 tail -2| head -n 1 | grep -q '0 bad' "
}

test_rlRpmPresent(){
    assertTrue "rlrpmPresent is reported to be obsoleted" "rlRpmPresent abcdefg |grep -q obsolete"
}


__checkLoggedText() {
  local msg="$1"
  local log="$2"
  assertTrue "__checkLoggedText logs '$msg' to the '$log'" "grep -q '$msg' $log"
}
