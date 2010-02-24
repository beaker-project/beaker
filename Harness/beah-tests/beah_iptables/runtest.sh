#!/bin/bash

# Source the common test script helpers
. /usr/bin/rhts_environment.sh

REBOOT_FILE=/var/cache/rhts/$RECIPETESTID/REBOOTED

run()
{
  echo "Running: $*"
  "$@"
}

if [[ -z "$DRY_RUN" ]]; then

dbg_run()
{
  run "$@"
}
dbg_run_noout()
{
  echo "Running: $* &> /dev/null"
  "$@" &> /dev/null
}

else

dbg_run()
{
  echo "Would run: $*"
}
dbg_run_noout()
{
  echo "Would run: $* &> /dev/null"
}

fi

beah_iptables_set()
{
# FIXME: Should limit access only to machines in recipeset (use -s IPADDR)
local port=${1:-12432}
dbg_run_noout iptables -D INPUT -p tcp -m state --state NEW -m tcp --dport $port -j ACCEPT
dbg_run iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport $port -j ACCEPT && \
dbg_run service iptables save
}

beah_iptables_wrap()
{
dbg_run service iptables -S
run "$@"
local answ=$?
dbg_run service iptables -S
return $answ
}

echo "Setting iptables"
if beah_iptables_wrap beah_iptables_set >> $OUTPUTFILE 2>&1; then
  report_result $TEST PASS 0
else
  report_result $TEST FAIL 0
fi

#cat $OUTPUTFILE

