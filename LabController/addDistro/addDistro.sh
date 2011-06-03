#!/bin/sh

export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export LANG=en_US.UTF-8

DISTPATH=$1
DIST=$2
FAMILYUPDATE=$3
ARCH=$4
VARIANT=$5
TPATH=$6

# Override the above settings in this file.
if [ -e "/etc/sysconfig/rhts_lab_import" ]; then
 . /etc/sysconfig/rhts_lab_import
fi

FAMILY=$(echo $FAMILYUPDATE | awk -F. '{print $1}')
UPDATE=$(echo $FAMILYUPDATE | awk -F. '{print $2}')

if [ -n "$rhts_redhat_com" ]; then
 pushd /var/lib/beaker/addDistro.d
 for PLUGIN in *
 do
    echo ./$PLUGIN "$ARCH" "$FAMILY" "$DIST" "$VARIANT" "$DISTPATH"
    ./$PLUGIN "$ARCH" "$FAMILY" "$DIST" "$VARIANT" "$DISTPATH"
 done
 popd
fi
