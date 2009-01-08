#!/bin/sh
#
# Find all modules and drivers for a given class device.
#

if [ $# != "1" ] ; then
	echo
	echo "Script to display the drivers and modules for a specified sysfs class device"
	echo "usage: $0 <CLASS_NAME>"
	echo
	echo "example usage:"
	echo "      $0 sda"
	echo "Will show all drivers and modules for the sda block device."
	echo
	exit 1
fi

DEV=$1

if test -e "$1"; then
	DEVPATH=$1
else
	# find sysfs device directory for device
	DEVPATH=$(find /sys/class -name "$1" | head -1)
	test -z "$DEVPATH" && DEVPATH=$(find /sys/block -name "$1" | head -1)
	test -z "$DEVPATH" && DEVPATH=$(find /sys/bus -name "$1" | head -1)
	if ! test -e "$DEVPATH"; then
		exit 1
	fi
fi

if test -L "$DEVPATH"; then
	# resolve class device link to device directory
	DEVPATH=$(readlink -f $DEVPATH)
fi

if test -d "$DEVPATH"; then
	# resolve old-style "device" link to the parent device
	PARENT="$DEVPATH";
	while test "$PARENT" != "/"; do
		if test -L "$PARENT/device"; then
			DEVPATH=$(readlink -f $PARENT/device)
			break
		fi
		PARENT=$(dirname $PARENT)
	done
fi

while test "$DEVPATH" != "/"; do
	DRIVERPATH=
	DRIVER=
	MODULEPATH=
	MODULE=
	if test -e $DEVPATH/driver; then
		DRIVERPATH=$(readlink -f $DEVPATH/driver)
		DRIVER=$(basename $DRIVERPATH)
		echo $DRIVER
		if test -e $DRIVERPATH/module; then
			MODULEPATH=$(readlink -f $DRIVERPATH/module)
			MODULE=$(basename $MODULEPATH)
			echo $MODULE
		fi
	fi

	DEVPATH=$(dirname $DEVPATH)
done
