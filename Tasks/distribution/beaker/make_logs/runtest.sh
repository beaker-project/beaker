!# /usr/bin/bash
. /usr/bin/rhts-environment.sh
. /usr/share/beakerlib/beakerlib.sh

function MakeLog()
{
 rlJournalStart
  rlPhaseStartSetup
   rlRun "for ((j=0;j<5;j++)); do echo 'blahblahblahblah'; done"
  rlPhaseEnd
 rlJournalEnd
}

for ((i=0;i < $SUBTASKS;i++)); do MakeLog;report_result TEST=$i PASS; done
exit 0

