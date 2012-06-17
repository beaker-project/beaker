#!/bin/sh

export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export LANG=en_US.UTF-8

DISTPATH=$1
DIST=$2
FAMILYUPDATE=$3
ARCHES=$4
VARIANTS=$5
TPATH=$6

# Override the above settings in this file.
if [ -e "/etc/sysconfig/beaker_lab_import" ]; then
 . /etc/sysconfig/beaker_lab_import
fi

FAMILY=$(echo $FAMILYUPDATE | awk -F. '{print $1}')
UPDATE=$(echo $FAMILYUPDATE | awk -F. '{print $2}')

if [ -n "$add_distro" ]; then
 pushd /var/lib/beaker/addDistro.d
 for PLUGIN in *
 do
    echo ./$PLUGIN "$ARCHES" "$FAMILY" "$DIST" "$VARIANTS" "$DISTPATH"
    ./$PLUGIN "$ARCHES" "$FAMILY" "$DIST" "$VARIANTS" "$DISTPATH"
 done
 popd
fi
