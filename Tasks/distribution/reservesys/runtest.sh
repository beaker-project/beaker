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
    echo " To return this system early. You can run the command: return2rhts.sh " >> $FILE
    echo "  Ensure you have your logs off the system before returning to RHTS   " >> $FILE
    echo "                                                                      " >> $FILE
    echo "      RHTS Test information:                                          " >> $FILE
    echo "                         HOSTNAME=$HOSTNAME                           " >> $FILE
    echo "                            JOBID=$JOBID                              " >> $FILE
    echo "                         RECIPEID=$RECIPEID                           " >> $FILE
    echo "                       LAB_SERVER=$LAB_SERVER                         " >> $FILE
    echo "                    RESULT_SERVER=$RESULT_SERVER                      " >> $FILE
    echo "                           DISTRO=$DISTRO                             " >> $FILE
    echo "                     ARCHITECTURE=$ARCH                               " >> $FILE
    echo "**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **" >> $FILE
}

RETURNSCRIPT()
{
    SCRIPT=/usr/bin/return2rhts.sh

    echo "#!/bin/sh"                           > $SCRIPT
    echo "export JOBID=$JOBID"                 >> $SCRIPT
    echo "export RECIPESETID=$RECIPETESTID"    >> $SCRIPT
    echo "export RECIPETYPE=$RECIPETYPE"       >> $SCRIPT
    echo "export RECIPEID=$RECIPEID"           >> $SCRIPT
    echo "export HOSTNAME=$HOSTNAME"           >> $SCRIPT
    echo "export UUID=$UUID"                   >> $SCRIPT
    echo "export LAB_SERVER=$LAB_SERVER"       >> $SCRIPT 
    echo "export RESULT_SERVER=$RESULT_SERVER" >> $SCRIPT
    echo "export TEST=$TEST"                   >> $SCRIPT
    echo "export TESTPATH=$TESTPATH"           >> $SCRIPT
    echo "export TESTORDER=$TESTORDER"         >> $SCRIPT
    echo "export TESTID=$TESTID"               >> $SCRIPT
    echo "export STANDALONE=$STANDALONE"       >> $SCRIPT
    echo "rhts_sync_set -s DONE"               >> $SCRIPT
    echo "rhts_sync_block -s DONE $STANDALONE" >> $SCRIPT
    echo "rhts_test_update.py $RESULT_SERVER $TESTID finish_time" >> $SCRIPT
    echo "rhts_recipe_update.py $RESULT_SERVER $RECIPEID finish_recipe" >> $SCRIPT
    echo "rhts_end_testing.py $LAB_SERVER $HOSTNAME $RECIPEID $UUID" >> $SCRIPT

    chmod 777 $SCRIPT
}

EXTENDTESTTIME()
{
    SCRIPT2=/usr/bin/extendtesttime.sh

    echo "#!/bin/sh"                           > $SCRIPT2
    echo "if [ "x\$1" == "x" ] ; then"         >> $SCRIPT2
    echo "  echo \"You must specify a time\""  >> $SCRIPT2
    echo "  echo \" in hours.\""               >> $SCRIPT2
    echo "  echo \"example: \$0 24h\""         >> $SCRIPT2
    echo "  exit 1"                            >> $SCRIPT2
    echo "fi"                                  >> $SCRIPT2
    echo "export LAB_SERVER=$LAB_SERVER"       >> $SCRIPT2
    echo "export HOSTNAME=$HOSTNAME"           >> $SCRIPT2
    echo "export JOBID=$JOBID"                 >> $SCRIPT2
    echo "export TEST=$TEST"                   >> $SCRIPT2
    echo "export TESTID=$TESTID"               >> $SCRIPT2
    echo "rhts_test_checkin.py $LAB_SERVER $HOSTNAME $JOBID $TEST $ARCH \$1 $TESTID" >> $SCRIPT2

    sed -i 's/#ARG#/$1/g' $SCRIPT2

    chmod 777 $SCRIPT2
}

NOTIFY()
{
    mail -s "$HOSTNAME" $SUBMITTER < /etc/motd
}

WATCHDOG()
{
    rhts_test_checkin.py $LAB_SERVER $HOSTNAME $JOBID $TEST $ARCH $SLEEPTIME $TESTID
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

WATCHDOG

EXTENDTESTTIME

RETURNSCRIPT

/sbin/service rhts stop

echo "***** End of reservesys test *****" >> $OUTPUTFILE

RprtRslt $TEST PASS 0

exit 0
