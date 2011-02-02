#!/bin/sh

# Source the common test script helpers
. /usr/bin/rhts_environment.sh

# Functions

#function to workaround the x86_64 virtual machine. This function will not
#check for "NMI appears to be stuck" message in the dmesg of the system if the
#machine is an x86_64 guest. For detailed info on this , please see:
# https://bugzilla.redhat.com/show_bug.cgi?id=500845 
# 
VirtWorkaround() 
{
    ARCH=$(arch)
    if [[ x"${ARCH}" == xx86_64 ]]; then 
       if [ -x ./hvm_detect ]; then 
          if ./hvm_detect; then 
             grep -v "NMI appears to be stuck" /usr/share/rhts/failurestrings > /usr/share/rhts/failurestrings.tmp 
             mv -f /usr/share/rhts/failurestrings.tmp /usr/share/rhts/failurestrings
          fi
       fi
    fi
}

RprtRslt()
{
    ONE=$1
    TWO=$2
    THREE=$3

    # File the results in the database
    report_result $ONE $TWO $THREE
}

SetUpInit()
{
    # Configure the init to display setup for serial
    sed -i s/BOOTUP=color/BOOTUP=serial/ /etc/sysconfig/init
}

CHECKRECIPE()
{
    if [ -e "/root/RECIPE.TXT" ]; then
        # If RECIPE.TXT exists then verify that its our recipe id, otherwise abort.
        EXISTINGID=$(cat /root/RECIPE.TXT)
        if [ "$RECIPEID" != "$EXISTINGID" ]; then
            echo "Recipe ID $EXISTINGID on disk doesn't match ours! Install fail?" >> $OUTPUTFILE
	    report_result $TEST/CheckRecipe FAIL
            rhts-abort -t recipeset
        fi
    else
        echo "No Recipe ID on disk! Install fail?" >> $OUTPUTFILE
	report_result $TEST/CheckRecipe FAIL
    fi
    report_result $TEST/CheckRecipe PASS
}

MOTD()
{
    FILE=/etc/motd

    echo "**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **" > $FILE
    echo "         This System is part of the Red Hat Test System.              " >> $FILE
    echo "                                                                      " >> $FILE
    echo "      Please do not use this system for individual unit testing.      " >> $FILE
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

SYSLOGLVL()
{
    # Configure a default log level so we can send our own messages to console
    echo "local2.info      /dev/console" >> /etc/syslog.conf
    /sbin/service syslog restart
}

SysReport ()
{
    OUTPUTFILE=`mktemp /tmp/tmp.XXXXXX`
    grep -q "release 3 " /etc/redhat-release 
    if [ $? -eq 0 ]; then
	modarg=-d
	modarg2=
    else
	modarg="-F description"
	modarg2="-F version"
    fi
    sysnode=$(/bin/uname -n)
    syskernel=$(/bin/uname -r)
    sysmachine=$(/bin/uname -m)
    sysprocess=$(/bin/uname -p)
    sysuname=$(/bin/uname -a)
    sysswap=$(/usr/bin/free -m | /bin/awk '{if($1=="Swap:") {print $2,"MB"}}')
    sysmem=$(/usr/bin/free -m | /bin/awk '{if($1=="Mem:") {print $2,"MB"}}')
    syscpu=$(/bin/cat /proc/cpuinfo | /bin/grep processor | wc -l)
    syslspci=$(/sbin/lspci > $FILEAREA/lspci.log)
    sysprocmem=$(hostname > $FILEAREA/procmem.log; /bin/cat /proc/meminfo >> $FILEAREA/procmem.log)
    if [ -f /etc/fedora-release ]; then
	sysrelease=$(/bin/cat /etc/fedora-release)
    else
	sysrelease=$(/bin/cat /etc/redhat-release)
    fi
    syscmdline=$(/bin/cat /proc/cmdline)
    sysnmiint=$(/bin/cat /proc/interrupts | /bin/grep -i nmi)
    if [ -e /etc/modprobe.conf ]; then
	sysmodprobe=$(/bin/cat /etc/modprobe.conf > $FILEAREA/modprobe.log)
    else
	if [ -d /etc/modprobe.d ]; then 
		for file in $(ls /etc/modprobe.d)
		do
			sysmodprobe=$(/bin/cat /etc/modprobe.d/${file} > ${FILEAREA}/${file})
		done
	fi
    fi
    for x in $(/sbin/lsmod | /bin/cut -f1 -d" " 2>/dev/null | /bin/grep -v Module 2>/dev/null ); do
	echo "Checking module information $x:" >> $FILEAREA/modinfo.log
	/sbin/modinfo $modarg $x >> $FILEAREA/modinfo.log
	if [ -n "$modarg2" ]; then
	    /sbin/modinfo $modarg2 $x >> $FILEAREA/modinfo.log
	fi
    done
    if [ -x /usr/sbin/sestatus ]; then
	syssestatus=$(/usr/sbin/sestatus >> $FILEAREA/selinux.log)
    fi
    if [ -x /usr/sbin/semodule ]; then
	echo "********** SELinux Module list **********" >> $FILEAREA/selinux.log
	syssemodulelist=$(/usr/sbin/semodule -l >> $FILEAREA/selinux.log)
    fi
    sysderror=$(/bin/cat $FILEAREA/boot.messages | grep -i error | grep -v BIOS >> $FILEAREA/derror.log)
    sysderror1=$(/bin/grep -i collision $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror2=$(/bin/grep -i fail $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror3=$(/bin/grep -i temperature $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror4=$(/bin/grep BUG: $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror5=$(/bin/grep INFO: $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror6=$(/bin/grep FATAL: $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror7=$(/bin/grep WARNING: $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror8=$(/bin/grep -i "command not found" $FILEAREA/boot.messages >> $FILEAREA/derror.log)
    sysderror9=$(/bin/cat $FILEAREA/boot.messages | grep avc: | grep -v granted >> $FILEAREA/avcerror.log)
    sysderror10=$(/bin/grep -ci "PAT not supported by CPU" $FILEAREA/boot.messages)
    if [ -e /root/install.log ]; then
	cp /root/install.log $FILEAREA/install.log
	sysierror=$(/bin/grep -i error: $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror1=$(/bin/grep -i collision $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror2=$(/bin/grep -i fail $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror3=$(/bin/grep -i "file not found" $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror4=$(/bin/grep -i "command not found" $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror5=$(/bin/grep -i "missing operand" $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror6=$(/bin/grep -i timeout $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror7=$(/bin/grep -i FATAL: $FILEAREA/install.log >> $FILEAREA/ierror.log)
	sysierror8=$(/bin/grep -i WARNING: $FILEAREA/install.log | grep -v "Header V3 DSA signature" >> $FILEAREA/ierror.log)
    fi
    if [ -e /root/anaconda-ks.cfg ]; then
	cp /root/anaconda-ks.cfg $FILEAREA/anaconda-ks.cfg
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $FILEAREA/anaconda-ks.cfg
    fi
    if [ -e /root/install_kernel.log ]; then
	cp /root/install_kernel.log $FILEAREA/install_kernel.log
	syskerror=$(/bin/grep -i error: $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror1=$(/bin/grep -i fail $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror2=$(/bin/grep -i "file not found" $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror3=$(/bin/grep -i "command not found" $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror4=$(/bin/grep -i timeout $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror5=$(/bin/grep -i FATAL: $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
	syskerror6=$(/bin/grep -i WARNING: $FILEAREA/install_kernel.log >> $FILEAREA/kerror.log)
    fi

    # upload bootloader config files
    if [ -e /boot/grub/grub.conf ]; then
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l /boot/grub/grub.conf
    fi

    if [ -e /boot/efi/efi/redhat/elilo.conf ]; then
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l /boot/efi/efi/redhat/elilo.conf
    fi

    if [ -e /etc/yaboot.conf ]; then
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l /etc/yaboot.conf
    fi

    if [ -e /etc/zipl.conf ]; then
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l /etc/zipl.conf
    fi

    echo "********** System Information **********" >> $OUTPUTFILE
    echo "Hostname                = $sysnode"       >> $OUTPUTFILE
    echo "Kernel Version          = $syskernel"     >> $OUTPUTFILE
    echo "Machine Hardware Name   = $sysmachine"    >> $OUTPUTFILE
    echo "Processor Type          = $sysprocess"    >> $OUTPUTFILE
    echo "uname -a output         = $sysuname"      >> $OUTPUTFILE
    echo "Swap Size               = $sysswap"       >> $OUTPUTFILE
    echo "Mem Size                = $sysmem"        >> $OUTPUTFILE
    echo "Number of Processors    = $syscpu"        >> $OUTPUTFILE
    echo "System Release          = $sysrelease"    >> $OUTPUTFILE
    echo "Command Line            = $syscmdline"    >> $OUTPUTFILE
    echo "System NMI Interrupts   = $sysnmiint"     >> $OUTPUTFILE
    echo "********** LSPCI **********"              >> $OUTPUTFILE
    /bin/cat $FILEAREA/lspci.log                    >> $OUTPUTFILE
    echo "********** Modprob **********"            >> $OUTPUTFILE
    /bin/cat $FILEAREA/modprobe.log                 >> $OUTPUTFILE
    echo "********** Module Information **********" >> $OUTPUTFILE
    /bin/cat $FILEAREA/modinfo.log                  >> $OUTPUTFILE
    if [ -x /usr/sbin/sestatus ]; then
	echo "********** SELinux Status **********" >> $OUTPUTFILE
	/bin/cat $FILEAREA/selinux.log              >> $OUTPUTFILE
    fi
    FAILURE=FALSE
    # Check dmesg log for issues
    dresult_count=0
    if [ -s $FILEAREA/derror.log ]; then
	dresult_count=$(/usr/bin/wc -l $FILEAREA/derror.log | awk '{print $1}')
	echo "******** Potential Issues dmesg ********" >> $OUTPUTFILE
	/bin/cat $FILEAREA/derror.log               >> $OUTPUTFILE
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $FILEAREA/boot.messages
	if [ "$sysderror10" -ne 0 ]; then
	    FAILURE=TRUE
	fi
    fi

    # Submit proc meminfo log
    if [ -e $FILEAREA/procmem.log ]; then
	rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $FILEAREA/procmem.log
    fi

    # Check dmesg log for avc failures
    if [ -s $FILEAREA/avcerror.log ]; then
	echo "******** SElinux AVC Failures ********" >> $OUTPUTFILE
	/bin/cat $FILEAREA/avcerror.log             >> $OUTPUTFILE
	FAILURE=TRUE
    fi
    iresult_count=0
    # Check install log for issues
    if [ -s $FILEAREA/ierror.log ]; then
	iresult_count=$(/usr/bin/wc -l $FILEAREA/ierror.log | awk '{print $1}')
	echo "***** Potential Issues install.log *****" >> $OUTPUTFILE
	/bin/cat $FILEAREA/ierror.log               >> $OUTPUTFILE
    fi
    kresult_count=0
    # Check kernel log for issues
    if [ -s $FILEAREA/kerror.log ]; then
	kresult_count=$(/usr/bin/wc -l $FILEAREA/kerror.log | awk '{print $1}')
	echo "* Potential Issues install_kernel.log *" >> $OUTPUTFILE
	/bin/cat $FILEAREA/kerror.log               >> $OUTPUTFILE
    fi
    echo "******** End System Information ********" >> $OUTPUTFILE
    if [ -s $FILEAREA/derror.log -o -s $FILEAREA/avcerror.log -o -s $FILEAREA/ierror.log -o -s $FILEAREA/kerror.log ]; then
	result_count=$(/usr/bin/printf "%03d%03d%03d\n" $dresult_count $iresult_count $kresult_count)
	if [ $FAILURE = TRUE ]; then
	    report_result $TEST/Sysinfo FAIL $result_count
	else
	    report_result $TEST/Sysinfo PASS $result_count
	fi
    else
	report_result $TEST/Sysinfo PASS 0
    fi
}

echo "***** Start of Install test *****" > $OUTPUTFILE

FILEAREA=/mnt/testarea
/bin/dmesg > $FILEAREA/boot.messages

CHECKRECIPE

MOTD

SetUpInit

SYSLOGLVL

VirtWorkaround

if [ -s "/root/install.log" ]; then
    echo "***** Begin install.log *****" >> $OUTPUTFILE
    cat /root/install.log >> $OUTPUTFILE
    echo "***** End install.log *****" >> $OUTPUTFILE
else
    echo "/root/install.log not found" >> $OUTPUTFILE
fi

if [ -s "/root/install.log.syslog" ]; then
    echo "***** Begin install.log.syslog *****" >> $OUTPUTFILE
    cat /root/install.log.syslog >> $OUTPUTFILE
    echo "***** End install.log.syslog *****" >> $OUTPUTFILE
else
    echo "/root/install.log.syslog not found" >> $OUTPUTFILE
fi

echo "***** End of Install test *****" >> $OUTPUTFILE

SCORE=$(rpm -qa | wc -l)
RprtRslt $TEST PASS $SCORE

if [ -s "/root/install_kernel.log" ]; then
    echo "***** Begin install_kernel.log *****" >> $OUTPUTFILE
    cat /root/install_kernel.log >> $OUTPUTFILE
    echo "***** End install_kernel.log *****" >> $OUTPUTFILE
    if [ -n "$TESTARGS" ]; then
	RUNKERNEL=$(/bin/uname -r)
	if [ $TESTARGS != $RUNKERNEL ]; then
	    echo "***** $TESTARGS != $RUNKERNEL *****" >> $OUTPUTFILE
	    RprtRslt $TEST/Select_kernel FAIL 1
	    if [ -f /etc/grub.conf ]; then
		grep $TESTARGS /etc/grub.conf
		if [ $? -eq 0 ]; then
		    echo "***** Kernel install Passed grub.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel PASS 0
		else
		    echo "***** Kernel install Failed grub.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel FAIL 1	    
		fi
	    fi
	    if [ -f /etc/elilo.conf ]; then
		grep $TESTARGS /etc/elilo.conf
		if [ $? -eq 0 ]; then
		    echo "***** Kernel install Passed elilo.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel PASS 0
		else
		    echo "***** Kernel install Failed elilo.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel FAIL 1	    
		fi
	    fi
	    if [ -f /boot/etc/yaboot.conf ]; then
		grep $TESTARGS /boot/etc/yaboot.conf
		if [ $? -eq 0 ]; then
		    echo "***** Kernel install Passed yaboot.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel PASS 0
		else
		    echo "***** Kernel install Failed yaboot.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel FAIL 1	    
		fi
	    fi
	    if [ -f /etc/zipl.conf ]; then
		# s390 strikes again, zipl entries can't be more than 15 chars
		grep default=$(echo $TESTARGS | cut -c1-15) /etc/zipl.conf
		if [ $? -eq 0 ]; then
		    echo "***** Kernel install Passed zipl.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel PASS 0
		else
		    echo "***** Kernel install Failed zipl.conf *****" >> $OUTPUTFILE
		    RprtRslt $TEST/Install_kernel FAIL 1	    
		fi
	    fi
	else
	    echo "***** $TESTARGS = $RUNKERNEL *****" >> $OUTPUTFILE
	    RprtRslt $TEST/Select_kernel PASS 0
	fi
    fi
fi

SysReport

exit 0
