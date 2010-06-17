#!/bin/sh

# Source the common test script helpers
. /usr/bin/rhts_environment.sh

STOPRHTS()
{
    chkconfig rhts
    if [ $? -eq 0 ]; then
        /sbin/service rhts stop
    else
        /usr/bin/killall rhts-test-runner.sh
    fi
}

if [ $REBOOTCOUNT -gt 0 ]; then
    STOPRHTS
    exit 0
fi

# Functions
RprtRslt()
{
    ONE=$1
    TWO=$2
    THREE=$3

    # File the results in the database
    report_result $ONE $TWO $THREE
}

MOTD()
{
    FILE=/etc/motd
    local inventory="https://beaker.engineering.redhat.com"
    local watchdog= system=
    if [[ -z "$CALLED_BY_BEAH" ]]; then
        watchdog="http://$RESULT_SERVER/cgi-bin/rhts/watchdog.cgi"
        system="http://$LAB_SERVER/cgi-bin/rhts/systems.cgi?fqdn=$HOSTNAME"
    else
        watchdog="$inventory/recipes/$RECIPEID"
        system="$inventory/view/$HOSTNAME"
    fi

    mv $FILE $FILE.orig
    cat <<END > $FILE
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
                 This System is reserved by $SUBMITTER.

 To return this system early. You can run the command: $return2pool
  Ensure you have your logs off the system before returning to $scheduler

 To extend your reservation time. You can run the command:
  extendtesttime.sh
 This is an interactive script. You will be prompted for how many
  hours you would like to extend the reservation.
  Please use this command responsibly, Everyone uses these machines.

 You should verify the watchdog was updated succesfully after
  you extend your reservation.
  $watchdog

 For ssh, kvm, serial and power control operations please look here:
  $system

      $scheduler Test information:
                         HOSTNAME=$HOSTNAME
                            JOBID=$JOBID
                         RECIPEID=$RECIPEID
                    RESULT_SERVER=$RESULT_SERVER
                           DISTRO=$DISTRO
                     ARCHITECTURE=$ARCH
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
END
}

RETURNSCRIPT()
{
    SCRIPT=/usr/bin/$return2pool

    echo "#!/bin/sh"                           > $SCRIPT
    echo "export RESULT_SERVER=$RESULT_SERVER" >> $SCRIPT
    echo "export TESTID=$TESTID" >> $SCRIPT
    echo "/usr/bin/rhts-test-update $RESULT_SERVER $TESTID finish" >> $SCRIPT
    echo "touch /var/cache/rhts/$TESTID/done" >> $SCRIPT
    if [[ -z "$CALLED_BY_BEAH" ]]; then
        echo "/bin/echo Hit Return to reboot the system and continue any" >> $SCRIPT
        echo "/bin/echo remaining RHTS tests. Or hit CTRL-C now if this" >> $SCRIPT
        echo "/bin/echo is not desired." >> $SCRIPT
        echo "read dummy" >> $SCRIPT
        echo "/usr/bin/rhts-reboot" >> $SCRIPT
    else
        echo "/bin/echo Going on..." >> $SCRIPT
        rm -f /usr/bin/return2rhts.sh &> /dev/null || true
        ln -s $SCRIPT /usr/bin/return2rhts.sh &> /dev/null || true
    fi

    chmod 777 $SCRIPT
}

EXTENDTESTTIME()
{
SCRIPT2=/usr/bin/extendtesttime.sh

cat > $SCRIPT2 <<-EOF
howmany()
{
if [ -z "\$1" ]; then
  read RESPONSE
else
  echo "How many hours would you like to extend the reservation."
  echo "             Must be between 1 and 99                   "
  RESPONSE="\$1"
fi
validint "\$RESPONSE" 1 99
echo "Extending reservation time \$RESPONSE"
EXTRESTIME=\$(echo \$RESPONSE)h
}

validint()
{
# validate first field.
number="\$1"; min="\$2"; max="\$3"

if [ -z "\$number" ] ; then
echo "You didn't enter anything."
exit 1
fi

if [ "\${number%\${number#?}}" = "-" ] ; then # first char '-' ?
testvalue="\${number#?}" # all but first character
else
testvalue="\$number"
fi

nodigits="\$(echo \$testvalue | sed 's/[[:digit:]]//g')"

if [ ! -z "\$nodigits" ] ; then
echo "Invalid number format! Only digits, no commas, spaces, etc."
exit 1
fi

if [ ! -z "\$min" ] ; then
if [ "\$number" -lt "\$min" ] ; then
echo "Your value is too small: smallest acceptable value is \$min"
exit 1
fi
fi
if [ ! -z "\$max" ] ; then
if [ "\$number" -gt "\$max" ] ; then
echo "Your value is too big: largest acceptable value is \$max"
exit 1
fi
fi

return 0
}

howmany "\$1"

export RESULT_SERVER=$RESULT_SERVER
export HOSTNAME=$HOSTNAME
export JOBID=$JOBID
export TEST=$TEST
export TESTID=$TESTID
rhts-test-checkin $RESULT_SERVER $HOSTNAME $JOBID $TEST \$EXTRESTIME $TESTID
logger -s "rhts-test-checkin $RESULT_SERVER $HOSTNAME $JOBID $TEST \$EXTRESTIME $TESTID"
EOF

chmod 777 $SCRIPT2
}

NOTIFY()
{
    /sbin/service sendmail start
    local msg=$(mktemp)
    local tag=
    [[ -n "$CALLED_BY_BEAH" ]] && tag="[Beaker Machine Reserved] "

cat > $msg <<-EOF
To: $SUBMITTER
Subject: $tag$HOSTNAME
X-$scheduler-test: $TEST

EOF
    cat /etc/motd >>$msg
    cat $msg | sendmail -t
    \rm -f $msg
}

WATCHDOG()
{
    rhts-test-checkin $RESULT_SERVER $HOSTNAME $JOBID $TEST $SLEEPTIME $TESTID
}

if [ -z "$RESERVETIME" ]; then
    SLEEPTIME=24h
else
    SLEEPTIME=$RESERVETIME
fi

if [ -n "$RESERVEBY" ]; then
    SUBMITTER=$RESERVEBY
fi

echo "***** Start of reservesys test *****" > $OUTPUTFILE

BUILD_()
{
    local scheduler= return2pool=
    if [[ -z "$CALLED_BY_BEAH" ]]; then
        scheduler=RHTS
        return2pool=return2rhts.sh
    else
        scheduler=Beaker
        return2pool=return2beaker.sh
    fi

    # build the /etc/motd file
    echo "***** Building /etc/motd *****" >> $OUTPUTFILE
    MOTD

    # send email to the submitter
    echo "***** Sending email to $SUBMITTER *****" >> $OUTPUTFILE
    NOTIFY

    # set the external watchdog timeout
    echo "***** Setting the external watchdog timeout *****" >> $OUTPUTFILE
    WATCHDOG

    # build /usr/bin/extendtesttime.sh script to allow user
    #  to extend the time time.
    echo "***** Building /usr/bin/extendtesttime.sh *****" >> $OUTPUTFILE
    EXTENDTESTTIME

    # build /usr/bin/$return2pool script to allow user
    #  to return the system to $scheduler early.
    echo "***** Building /usr/bin/$return2pool *****" >> $OUTPUTFILE
    RETURNSCRIPT
}

BUILD_

echo "***** End of reservesys test *****" >> $OUTPUTFILE
RprtRslt $TEST PASS 0

# stop rhts service, So that reserve workflow works with test reboot support.
STOPRHTS
