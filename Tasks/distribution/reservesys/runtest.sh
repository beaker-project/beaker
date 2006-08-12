#!/bin/sh

# Source the common test script helpers
. /usr/bin/rhts_environment.sh

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

    echo "**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **" > $FILE
    echo "                 This System is reserved by $SUBMITTER.               " >> $FILE
    echo "                                                                      " >> $FILE
    echo "                                                                      " >> $FILE
    echo "      RHTS Test information:                                          " >> $FILE
    echo "                         HOSTNAME=$HOSTNAME                           " >> $FILE
    echo "                            JOBID=$JOBID                              " >> $FILE
    echo "                         RECIPEID=$RECIPEID                           " >> $FILE
    echo "                       LAB_SERVER=$LAB_SERVER                         " >> $FILE
    echo "                    RESULT_SERVER=$RESULT_SERVER                      " >> $FILE
    echo "                           DISTRO=$DISTRO                             " >> $FILE
    echo "**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **" >> $FILE
}

NOTIFY()
{
    mail -s "$HOSTNAME" $SUBMITTER < /etc/motd
}

if [ -z "$RESERVETIME" ]; then
    SLEEPTIME=24h
else
    SLEEPTIME=$RESERVETIME
fi

if [ -z "$RESERVEBY" ]; then
    SUBMITTER=Uknown
else
    SUBMITTER=$RESERVEBY
fi

echo "***** Start of reservesys test *****" > $OUTPUTFILE

MOTD

NOTIFY

sleep $SLEEPTIME

echo "***** End of reservesys test *****" >> $OUTPUTFILE

RprtRslt $TEST PASS 0

exit 0
