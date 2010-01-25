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

function sub_beah_update()
{
cat >/etc/yum.repos.d/epel.repo <<END
[epel1]
name=epel1
baseurl=http://download.fedora.redhat.com/pub/epel/\$releasever/\$basearch
enabled=1
gpgcheck=0
END

CONF_TEMP_DIR=/tmp/beah-conf

# PREPARE:
mkdir $CONF_TEMP_DIR
for beahconf in /etc/beah*.conf; do
  cp $beahconf $CONF_TEMP_DIR
done

# REMOVE OLD:
#rpm -e beah
yum -y erase beah

# INSTALL:
yum -y install git
mkdir -p /tmp/beah-new
pushd /tmp/beah-new
git clone "${BEAH_GIT_REPO:-"git://git.fedorahosted.org/git/beaker.git"}"
cd beaker
git checkout "${BEAH_GIT_BRANCH:-"origin/Scheduler"}"
cd Harness
rm -f bin/beah_python # FIXME: get rid of this relict... It must come from master branch.
BEAH_DEV=".dev$(date "+%Y%m%d%H%M")" python setup.py install
popd

# RESTORE CONF:
for beahconf in $CONF_TEMP_DIR/beah*.conf; do
  cp $beahconf /etc
done
}

function sub_reboot()
{
  echo "***** Phase 1: rebooting machine *****" >> $OUTPUTFILE
  mkdir -p /var/cache/rhts/$RECIPETESTID >> $OUTPUTFILE 2>&1
  touch "$REBOOT_FILE" >> $OUTPUTFILE 2>&1
  rhts-reboot
  # rhts-reboot should block and wait until machine is rebooted.
  report_result $TEST/reboot FAIL 0
  exit 1
}

BEAH_OUT=/tmp/beah-output
if [[ -e "$REBOOT_FILE" ]]; then
  /usr/bin/rhts-submit-log -l $BEAH_OUT
  report_result $TEST PASS 0
else
  sub_beah_update &> $BEAH_OUT
  sub_reboot
fi

