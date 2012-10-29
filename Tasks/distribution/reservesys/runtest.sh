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
    mv $FILE $FILE.orig

    local admonition=
    if [ -n "$BEAKER_RESERVATION_POLICY_URL" ] ; then
        admonition="
 Please ensure that you adhere to the reservation policy
  for Beaker systems:
  ${BEAKER_RESERVATION_POLICY_URL}"
    fi

    cat <<END > $FILE
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
                 This System is reserved by $SUBMITTER.

 To return this system early. You can run the command: return2beaker.sh
  Ensure you have your logs off the system before returning to Beaker

 To extend your reservation time. You can run the command:
  extendtesttime.sh
 This is an interactive script. You will be prompted for how many
  hours you would like to extend the reservation.${admonition}

 You should verify the watchdog was updated succesfully after
  you extend your reservation.
  ${BEAKER}recipes/$RECIPEID

 For ssh, kvm, serial and power control operations please look here:
  ${BEAKER}view/$HOSTNAME

      Beaker Test information:
                         HOSTNAME=$HOSTNAME
                            JOBID=$JOBID
                         RECIPEID=$RECIPEID
                    RESULT_SERVER=$RESULT_SERVER
                           DISTRO=$DISTRO
                     ARCHITECTURE=$ARCH

      Job Whiteboard: $BEAKER_JOB_WHITEBOARD

      Recipe Whiteboard: $BEAKER_RECIPE_WHITEBOARD
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
END
}

RETURNSCRIPT()
{
    SCRIPT=/usr/bin/return2beaker.sh

    echo "#!/bin/sh"                           > $SCRIPT
    echo "export RESULT_SERVER=$RESULT_SERVER" >> $SCRIPT
    echo "export TESTID=$TESTID" >> $SCRIPT
    echo "/usr/bin/rhts-test-update $RESULT_SERVER $TESTID finish" >> $SCRIPT
    echo "touch /var/cache/rhts/$TESTID/done" >> $SCRIPT
    echo "/bin/echo Going on..." >> $SCRIPT
    rm -f /usr/bin/return2rhts.sh &> /dev/null || true
    ln -s $SCRIPT /usr/bin/return2rhts.sh &> /dev/null || true

    chmod 777 $SCRIPT
}

EXTENDTESTTIME()
{
SCRIPT2=/usr/bin/extendtesttime.sh

cat > $SCRIPT2 <<-EOF
howmany()
{
if [ -n "\$1" ]; then
  RESPONSE="\$1"
else
  echo "How many hours would you like to extend the reservation."
  echo "             Must be between 1 and 99                   "
  read RESPONSE
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

cat > $msg <<-EOF
To: $SUBMITTER
Subject: [Beaker Machine Reserved] $HOSTNAME
X-Beaker-test: $TEST

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
    # Verify the max amount of time a system can be reserved
    if [ $SLEEPTIME -gt 356400 ]; then
        RprtRslt $TEST/watchdog_exceeds_limit Warn $SLEEPTIME
	SLEEPTIME=356400
    fi
fi

if [ -n "$RESERVEBY" ]; then
    SUBMITTER=$RESERVEBY
fi

echo "***** Start of reservesys test *****" > $OUTPUTFILE

BUILD_()
{
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

    # build /usr/bin/return2beaker.sh script to allow user
    #  to return the system to Beaker early.
    echo "***** Building /usr/bin/return2beaker.sh *****" >> $OUTPUTFILE
    RETURNSCRIPT
}

if [ -n "$RESERVE_IF_FAIL" ]; then
    ./recipe_status
    if [ $? -eq 0 ]; then
        RprtRslt $TEST PASS 0
        exit 0
    fi
fi

BUILD_

echo "***** End of reservesys test *****" >> $OUTPUTFILE
RprtRslt $TEST PASS 0

# stop rhts service, So that reserve workflow works with test reboot support.
STOPRHTS
