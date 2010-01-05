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

__testLogFce() {
  # This should help us to test various logging functions
  # which takes <message> and optional <logfile> parameters
  rlJournalStart
  local log=$( mktemp )
  local myfce=$1
  $myfce "MessageABC" &>/dev/null
  assertTrue "rlHeadLog to OUTPUTFILE" "grep -q 'MessageABC' $OUTPUTFILE"
  rm -f $log   # remove the log, so it have to be created
  $myfce "MessageDEF" $log &>/dev/null
  assertTrue "rlHeadLog to nonexisting log" "grep -q 'MessageDEF' $log"
  touch $log   # create the log if it still do not exists
  $myfce "MessageGHI" $log &>/dev/null
  assertTrue "rlHeadLog to existing log" "grep -q 'MessageGHI' $log"
  $myfce "MessageJKL" $log &>/dev/null
  assertTrue "rlHeadLog only adds to the log (do not overwrite it)" "grep -q 'MessageGHI' $log"
  assertTrue "rlHeadLog adds to the log" "grep -q 'MessageJKL' $log"
  assertTrue "$myfce logs to STDOUT" "$myfce $myfce-MNO |grep -q '$myfce-MNO'"
  assertTrue "$myfce creates journal entry" "rlJournalPrint |grep -q '$myfce-MNO'"
}

test_rlHeadLog() {
  __testLogFce rlHeadLog
}

test_rlLog() {
  __testLogFce rlLog
}
test_rlLogDebug() {
  #only works when DEBUG is set
  DEBUG=1
  __testLogFce rlLogDebug
  DEBUG=0
}
test_rlLogInfo() {
  __testLogFce rlLogInfo
}
test_rlLogWarning() {
  __testLogFce rlLogWarning
}
test_rlLogError() {
  __testLogFce rlLogError
}
test_rlLogFatal() {
  __testLogFce rlLogFatal
}

test_rlDie(){
	#dunno how to test this - it contains untestable helpers like rlBundleLogs and rlReport
	echo "rlDie skipped"
}

test_rlPhaseStartEnd(){
  rlJournalStart ; rlPhaseStart FAIL    &> /dev/null
  #counting passes and failures
  rlAssert0 "failed assert #1" 1        &> /dev/null
  rlAssert0 "successfull assert #1" 0   &> /dev/null
  rlAssert0 "failed assert #2" 1        &> /dev/null
  rlAssert0 "successfull assert #2" 0   &> /dev/null
  assertTrue "passed asserts were stored" "rlJournalPrintText |grep '2 good'"
  assertTrue "failed asserts were stored" "rlJournalPrintText |grep '2 bad'"
  #new phase resets score
  rlPhaseEnd &> /dev/null ; rlPhaseStart FAIL &> /dev/null
  assertTrue "passed asserts were reseted" "rlJournalPrintText |grep '0 good'"
  assertTrue "failed asserts were reseted" "rlJournalPrintText |grep '0 bad'"

  assertFalse "creating phase without type doesn't succeed" "rlPhaseEnd ; rlPhaseStart &> /dev/null"
  assertFalse "phase without type is not inserted into journal" "rlJournalPrint |grep -q '<phase.*type=\"\"'"
  assertFalse "creating phase with unknown type doesn't succeed" "rlPhaseEnd ; rlPhaseStart ZBRDLENI &> /dev/null"
  assertFalse "phase with unknown type is not inserted into journal" "rlJournalPrint |grep -q '<phase.*type=\"ZBRDLENI\"'"
  rm -rf $BEAKERLIB_DIR
}

test_rlPhaseStartShortcuts(){
  rlJournalStart
  rlPhaseStartSetup &> /dev/null
  assertTrue "setup phase with ABORT type found in journal" "rlJournalPrint |grep -q '<phase.*type=\"ABORT\"'"
  rm -rf $BEAKERLIB_DIR

  rlJournalStart
  rlPhaseStartTest &> /dev/null
  assertTrue "test phase with FAIL type found in journal" "rlJournalPrint |grep -q '<phase.*type=\"FAIL\"'"
  rm -rf $BEAKERLIB_DIR

  rlJournalStart
  rlPhaseStartCleanup &> /dev/null
  assertTrue "clean-up phase with WARN type found in journal" "rlJournalPrint |grep -q '<phase.*type=\"WARN\"'"
  rm -rf $BEAKERLIB_DIR
}

test_oldMetrics(){
    assertTrue "rlLogHighMetric is marked as deprecated" \
        "rlLogHighMetric MTR-HIGH-OLD 1 |grep -q deprecated"
    assertTrue "rlLogLowMetric is marked as deprecated" \
        "rlLogLowMetric MTR-LOW-OLD 1 |grep -q deprecated"
}
test_rlShowPkgVersion(){
    assertTrue "rlShowPkgVersion is marked as deprecated" \
        "rlShowPkgVersion |grep -q obsoleted"
}


test_LogMetricLowHigh(){
    rlJournalStart ; rlPhaseStart FAIL &> /dev/null
    assertTrue "low metric inserted to journal" "rlLogMetricLow metrone 123 "
    assertTrue "high metric inserted to journal" "rlLogMetricHigh metrtwo 567"
    assertTrue "low metric found in journal" "rlJournalPrint |grep -q '<metric.*name=\"metrone\".*type=\"low\"'"
    assertTrue "high metric found in journal" "rlJournalPrint |grep -q '<metric.*name=\"metrtwo\".*type=\"high\"'"

    #second metric called metrone - must not be inserted to journal
    rlLogMetricLow metrone 345
    assertTrue "metric insertion fails when name's not unique inside one phase" \
            "[ `rlJournalPrint | grep -c '<metric.*name=.metrone.*type=.low.'` -eq 1 ]"
    rm -rf $BEAKERLIB_DIR

    #same name of metric but in different phases - must work
    rlJournalStart ; rlPhaseStartTest phase-1 &> /dev/null
    rlLogMetricLow metrone 345
    rlPhaseEnd &> /dev/null ; rlPhaseStartTest phase-2 &> /dev/null
    rlLogMetricLow metrone 345
    assertTrue "metric insertion succeeds when name's not unique but phases differ" \
            "[ `rlJournalPrint | grep -c '<metric.*name=.metrone.*type=.low.'` -eq 2 ]"
}

test_rlShowRunningKernel(){
	rlJournalStart; rlPhaseStart FAIL &> /dev/null
	rlShowRunningKernel &> /dev/null
	assertTrue "kernel version is logged" "rlJournalPrintText |grep -q `uname -r`"
}

__checkLoggedPkgInfo() {
  local log=$1
  local msg=$2
  local name=$3
  local version=$4
  local release=$5
  local arch=$6
  assertTrue "rlShowPackageVersion logs name $msg" "grep -q '$name' $log"
  assertTrue "rlShowPackageVersion logs version $msg" "grep -q '$version' $log"
  assertTrue "rlShowPackageVersion logs release $msg" "grep -q '$release' $log"
  assertTrue "rlShowPackageVersion logs arch $msg" "grep -q '$arch' $log"
}

test_rlShowPackageVersion() {
  local log=$( mktemp )
  local list=$( mktemp )

  # Exit value shoud be defined
  assertFalse "rlShowPackageVersion calling without options" "rlShowPackageVersion"
  : >$OUTPUTFILE

  rpm -qa --qf "%{NAME}\n" > $list
  local first=$( tail -n 1 $list )
  local first_n=$( rpm -q $first --qf "%{NAME}\n" | tail -n 1 )
  local first_v=$( rpm -q $first --qf "%{VERSION}\n" | tail -n 1 )
  local first_r=$( rpm -q $first --qf "%{RELEASE}\n" | tail -n 1 )
  local first_a=$( rpm -q $first --qf "%{ARCH}\n" | tail -n 1 )

  # Test with 1 package
  rlShowPackageVersion $first &>/dev/null
  __checkLoggedPkgInfo $OUTPUTFILE "of 1 pkg" $first_n $first_v $first_r $first_a
  : >$OUTPUTFILE

  # Test with package this_package_do_not_exist
  assertTrue 'rlShowPackageVersion returns 1 when package do not exists' 'rlShowPackageVersion this_package_do_not_exist; [ $? -eq 1 ]'   # please use "'" - we do not want "$?" to be expanded too early
  assertTrue 'rlShowPackageVersion logs warning about this_package_do_not_exist' "grep -q 'this_package_do_not_exist' $OUTPUTFILE"
  : >$OUTPUTFILE

  # Test with few packages
  local few=$( tail -n 10 $list )
  rlShowPackageVersion $few &>/dev/null
  for one in $few; do
    local one_n=$( rpm -q $one --qf "%{NAME}\n" | tail -n 1 )
    local one_v=$( rpm -q $one --qf "%{VERSION}\n" | tail -n 1 )
    local one_r=$( rpm -q $one --qf "%{RELEASE}\n" | tail -n 1 )
    local one_a=$( rpm -q $one --qf "%{ARCH}\n" | tail -n 1 )
    __checkLoggedPkgInfo $OUTPUTFILE "of few pkgs" $one_n $one_v $one_r $one_a
  done
  : >$OUTPUTFILE

  # Test with package this_package_do_not_exist
  assertTrue 'rlShowPackageVersion returns 1 when some packages do not exists' "rlShowPackageVersion this_package_do_not_exist $few this_package_do_not_exist_too; [ \$? -eq 1 ]"
  : >$OUTPUTFILE

  rm -f $list
}



test_rlGetArch() {
  local out=$(rlGetArch)
  assertTrue 'rlGetArch returns 0' "[ $? -eq 0 ]"
  [ "$out" = 'i386' ] && out='i.8.'   # funny reg exp here
  uname -a | grep -q "$out"
  assertTrue 'rlGetArch returns correct arch' "[ $? -eq 0 ]"
}

test_rlGetDistroRelease() {
  local out=$(rlGetDistroRelease)
  assertTrue 'rlGetDistroRelease returns 0' "[ $? -eq 0 ]"
  grep -q -i "$out" /etc/redhat-release
  assertTrue 'rlGetDistroRelease returns release which is in the /etc/redhat-release' "[ $? -eq 0 ]"
}

test_rlGetDistroVariant() {
  local out=$(rlGetDistroVariant)
  assertTrue 'rlGetDistroVariant returns 0' "[ $? -eq 0 ]"
  grep -q -i "$out" /etc/redhat-release
  assertTrue 'rlGetDistroRelease returns variant which is in the /etc/redhat-release' "[ $? -eq 0 ]"
}



test_rlBundleLogs() {
  local prefix=rlBundleLogs-unittest
  rm -rf $prefix* CP-$prefix*.tar.gz
  # Prepare files which will be backed up
  mkdir $prefix
  mkdir $prefix/first
  echo "hello" > $prefix/first/greet
  echo "world" > $prefix/first_greet
  # Prepare fake rhts_submit_log utility
  cat <<EOF >$prefix/rhts_submit_log
#!/bin/sh
while [ \$# -gt 0 ]; do
  case "\$1" in
    -S|-T) shift; ;;
    -l) shift; cp "\$1" "CP-\$1";;
  esac
  shift
done
EOF
  chmod +x $prefix/rhts_submit_log
  PATH_orig="$PATH"
  export PATH="$( pwd )/$prefix:$PATH"
  # Run the rlBundleLogs function
  rlBundleLogs $prefix $prefix/first/greet $prefix/first_greet &> /dev/null
  assertTrue 'rlBundleLogs <some files> returns 0' "[ $? -eq 0 ]"
  export PATH="$PATH_orig"
  # Check if it did everithing it should
  assertTrue 'rlBundleLogs creates *.tar.gz file' \
        "ls CP-$prefix*.tar.gz &> /dev/null"
  mkdir $prefix-extracted
  tar -xzf CP-$prefix*.tar.gz -C $prefix-extracted
  assertTrue 'rlBundleLogs included first/greet file' \
        "grep -qr 'hello' $prefix-extracted/*"
  assertTrue 'rlBundleLogs included first_greet file' \
        "grep -qr 'world' $prefix-extracted/*"
  # Cleanup
  rm -rf $prefix* CP-$prefix*.tar.gz
}

test_LOG_LEVEL(){
	unset LOG_LEVEL
	unset DEBUG

	assertFalse "rlLogInfo msg not in journal dump with default LOG_LEVEL" \
	"rlLogInfo 'lllll' ; rlJournalPrintText |grep 'lllll'"

	assertTrue "rlLogWarning msg in journal dump with default LOG_LEVEL" \
	"rlLogWarning 'wwwwww' ; rlJournalPrintText |grep 'wwwww'"

	DEBUG=1
	assertTrue "rlLogInfo msg  in journal dump with default LOG_LEVEL but DEBUG turned on" \
	"rlLogInfo 'lllll' ; rlJournalPrintText |grep 'lllll'"
	unset DEBUG

	local LOG_LEVEL="INFO"
	assertTrue "rlLogInfo msg in journal dump with LOG_LEVEL=INFO" \
	"rlLogInfo 'lllll' ; rlJournalPrintText |grep 'lllll'"

	local LOG_LEVEL="WARNING"
	assertFalse "rlLogInfo msg not in journal dump with LOG_LEVEL higher than INFO" \
	"rlLogInfo 'lllll' ; rlJournalPrintText |grep 'lllll'"

	unset LOG_LEVEL
	unset DEBUG
}

test_rlFileSubmit() {
  local main_dir=`pwd`
  local prefix=rlFileSubmit-unittest
  local upload_to=$prefix/uploaded
  local hlp_files=$prefix/hlp_files
  mkdir -p $upload_to
  mkdir -p $hlp_files
  sync
  # Prepare fake rhts_submit_log utility
  cat <<EOF >$prefix/rhts_submit_log
#!/bin/sh
while [ \$# -gt 0 ]; do
  case "\$1" in
    -S|-T) shift; ;;
    -l) shift; cp "\$1" "$main_dir/$upload_to/";;
  esac
  shift
done
EOF
  chmod +x $prefix/rhts_submit_log
  ln -s rhts_submit_log $prefix/rhts-submit-log
  PATH_orig="$PATH"
  export PATH="$( pwd )/$prefix:$PATH"
  
  # TEST 1: No relative or absolute path specified
  local orig_file="$hlp_files/rlFileSubmit_test1.file"
  local alias="rlFileSubmit_test1.file"
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test1" > $orig_file
  
  cd $hlp_files
  rlFileSubmit rlFileSubmit_test1.file &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs file without relative or absolute path specified' "[ $? -eq 0 ]"
   
  # TEST 2: Relative path ./
  local orig_file="$hlp_files/rlFileSubmit_test2.file"
  local alias=`echo "$main_dir/$orig_file" | tr '/' "-" | sed "s/^-*//"`
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test2" > $orig_file
  
  cd $hlp_files
  rlFileSubmit ./rlFileSubmit_test2.file &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs relative path ./' "[ $? -eq 0 ]"
  
  # TEST 3: Relative path ../
  mkdir $hlp_files/directory/
  local orig_file="$hlp_files/rlFileSubmit_test3.file"
  local alias=`echo "$main_dir/$orig_file" | tr '/' "-" | sed "s/^-*//"`
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test3" > $orig_file
  
  cd $hlp_files/directory
  rlFileSubmit ../rlFileSubmit_test3.file &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs relative path ../' "[ $? -eq 0 ]"

  # TEST 4: Absolute path
  local orig_file="$hlp_files/rlFileSubmit_test4.file"
  local alias=`echo "$main_dir/$orig_file" | tr '/' "-" | sed "s/^-*//"`
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test4" > $orig_file
  
  rlFileSubmit $main_dir/$orig_file &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs absolute path' "[ $? -eq 0 ]"
  
  # TEST 5: Custom alias
  local orig_file="$hlp_files/rlFileSubmit_test5file"
  local alias="alias_rlFileSubmit_test5.file"
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test5" > $orig_file
  
  rlFileSubmit $orig_file $alias &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs custom alias' "[ $? -eq 0 ]"

  # TEST 6: Custom separator
  local orig_file="$hlp_files/rlFileSubmit_test6.file"
  local alias=`echo "$main_dir/$orig_file" | tr '/' "_" | sed "s/^_*//"`
  local expected_file="$upload_to/$alias"
  
  echo "rlFileSubmit_test6" > $orig_file
  
  rlFileSubmit -s '_' $main_dir/$orig_file &> /dev/null
  
  cd $main_dir
  local sum1=`md5sum $orig_file | cut -d " " -f 1`
  local sum2=`md5sum $expected_file | cut -d " " -f 1`
  
  [ -e $expected_file -a  "$sum1" = "$sum2" ]
  assertTrue 'rlBundleLogs absolute path' "[ $? -eq 0 ]"

  # Cleanup
  export PATH="$PATH_orig"
  rm -rf $prefix*
}
