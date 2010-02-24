#!/bin/bash

# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# FIXME:
# - change "/usr/bin/env python" to "$PYBIN" (full path)
#   - "/usr/bin/env python2.5" does not work in a_task :-(
#   - This should be done by setup.py!

(

## BEAH_TEMP - directory used to store downloaded files and for building
## components.
echo "BEAH_TEMP=${BEAH_TEMP:="/root/beah"}"

## PYTHON:
## PY_VER - version of python to build. Uncomment to include python in
## installation.
#PY_VER=2.5 # This is known to work on RHEL4.8
#PY_VER=2.6.2

## PYBIN_NAME - python interpreter binary to install harness to.
#PYBIN_NAME=python2.6
echo "PYBIN_NAME=${PYBIN_NAME:="python"}"

## ZOPE INTERFACE:
## ZI_VER - version of zope-interface to download and build. Uncomment to
## include zope-interface in installation.
echo "ZI_VER=${ZI_VER:="3.3.0"}"

## TWISTED:
## TW_VER - version of Twisted framework to download and build. Uncomment to
## include Twisted in installation.
echo "TW_VER=${TW_VER:="8.2.0"}"

## SETUPTOOLS:
## ST_VER - version of setuptools module to download and build. Uncomment to
## include setuptools in installation.
echo "ST_VER=${ST_VER:="0.6c11"}"

## SIMPLEJSON:
## SJ_VER - version of simplejson module to download and build. Uncomment to
## include simplejson in installation.
echo "SJ_VER=${SJ_VER:="2.0.9"}"

## UUID:
## UUID_VER - version of uuid module to download and build. Uncomment to
## include uuid in installation. No necessary on python2.5 and newer.
echo "UUID_VER=${UUID_VER:="1.30"}"

## HASHLIB:
## HL_VER - version of hashlib module to download and build. Uncomment to
## include uuid in installation. No necessary on python2.5 and newer.
echo "HL_VER=${HL_VER:="20081119"}"

## GIT:
## GIT_VER - version of git to download and build. Uncomment to include git in
## installation.
## this did not work on 4.8
#GIT_VER=1.6.4.1

## BEAKER:
#BKR=

################################################################################

mkdir -p $BEAH_TEMP
pushd $BEAH_TEMP

################################################################################
# BUILD AND INSTALL NEWER PYTHON (E.G. 2.5):
################################################################################
if [[ -n "$PY_VER" && "$PY_VER" != "-" ]]; then
mkdir python
pushd python

(
wget http://www.python.org/ftp/python/${PY_VER}/Python-${PY_VER}.tar.bz2 && \
tar xvjf Python-${PY_VER}.tar.bz2 && \
cd Python-${PY_VER} && \
./configure && \
make && \
{ make test || true; } && \
make altinstall
echo $? > ${BEAH_TEMP}/python.rc
) | tee ${BEAH_TEMP}/python.out 2> ${BEAH_TEMP}/python.err

PY_OK=`cat ${BEAH_TEMP}/python.rc`

popd
else
PY_OK=0
fi

## PYBIN - full name of python binary. See PYBIN_NAME.
PYBIN=`which $PYBIN_NAME`

################################################################################
# BUILD AND INSTALL ZOPE.INTERFACE:
################################################################################
if [[ -n "$ZI_VER" && "$ZI_VER" != "-" ]]; then
mkdir zope
pushd zope

(
wget http://www.zope.org/Products/ZopeInterface/${ZI_VER}/zope.interface-${ZI_VER}.tar.gz && \
tar xvzf zope.interface-${ZI_VER}.tar.gz && \
cd zope.interface-${ZI_VER} && \
$PYBIN setup.py build && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/zope-interface.rc
) | tee ${BEAH_TEMP}/zope-interface.out 2> ${BEAH_TEMP}/zope-interface.err

ZI_OK=`cat ${BEAH_TEMP}/zope-interface.rc`

popd
else
ZI_OK=0
fi

################################################################################
# BUILD AND INSTALL TWISTED:
################################################################################
if [[ -n "$TW_VER" && "$TW_VER" != "-" ]]; then
mkdir twisted
pushd twisted

(
wget http://tmrc.mit.edu/mirror/twisted/Twisted/8.2/Twisted-${TW_VER}.tar.bz2 && \
tar xvjf Twisted-${TW_VER}.tar.bz2 && \
cd Twisted-${TW_VER} && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/twisted.rc
) | tee ${BEAH_TEMP}/twisted.out 2> ${BEAH_TEMP}/twisted.err

TW_OK=`cat ${BEAH_TEMP}/twisted.rc`

popd
else
TW_OK=0
fi

################################################################################
# BUILD AND INSTALL GIT:
################################################################################
if [[ -n "$GIT_VER" && "$GIT_VER" != "-" ]]; then
mkdir git
pushd git

(
wget http://kernel.org/pub/software/scm/git/git-${GIT_VER}.tar.bz2 && \
tar xvjf git-${GIT_VER}.tar.bz2 && \
cd git-${GIT_VER} && \
make configure && \
./configure --prefix=/usr/local && \
make all doc && \
make check && \
make install
echo $? > ${BEAH_TEMP}/git.rc
) | tee ${BEAH_TEMP}/git.out 2> ${BEAH_TEMP}/git.err

GIT_OK=`cat ${BEAH_TEMP}/git.rc`

popd
else
GIT_OK=0
fi

################################################################################
# BUILD AND INSTALL SETUPTOOLS:
################################################################################
if [[ -n "$ST_VER" && "$ST_VER" != "-" ]]; then
mkdir setuptools
pushd setuptools

(
wget http://pypi.python.org/packages/source/s/setuptools/setuptools-${ST_VER}.tar.gz && \
tar xvzf setuptools-${ST_VER}.tar.gz && \
cd setuptools-${ST_VER} && \
$PYBIN setup.py build && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/setuptools.rc
) | tee ${BEAH_TEMP}/setuptools.out 2> ${BEAH_TEMP}/setuptools.err

ST_OK=`cat ${BEAH_TEMP}/setuptools.rc`

popd
else
ST_OK=0
fi

################################################################################
# BUILD AND INSTALL SIMPLEJSON:
################################################################################
if [[ -n "$SJ_VER" && "$SJ_VER" != "-" ]]; then
mkdir simplejson
pushd simplejson

(
wget http://pypi.python.org/packages/source/s/simplejson/simplejson-2.0.9.tar.gz && \
tar xvzf simplejson-${SJ_VER}.tar.gz && \
cd simplejson-${SJ_VER} && \
$PYBIN setup.py build && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/simplejson.rc
) | tee ${BEAH_TEMP}/simplejson.out 2> ${BEAH_TEMP}/simplejson.err

SJ_OK=`cat ${BEAH_TEMP}/simplejson.rc`

popd
else
SJ_OK=0
fi

################################################################################
# BUILD AND INSTALL UUID:
################################################################################
if [[ -n "$UUID_VER" && "$UUID_VER" != "-" && "`python -V 2>&1`" < "Python 2.5" ]]; then
mkdir uuid
pushd uuid

(
wget http://pypi.python.org/packages/source/u/uuid/uuid-${UUID_VER}.tar.gz && \
tar xvzf uuid-${UUID_VER}.tar.gz && \
cd uuid-${UUID_VER} && \
$PYBIN setup.py build && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/uuid.rc
) | tee ${BEAH_TEMP}/uuid.out 2> ${BEAH_TEMP}/uuid.err

UUID_OK=`cat ${BEAH_TEMP}/uuid.rc`

popd
else
UUID_OK=0
fi

################################################################################
# BUILD AND INSTALL HASHLIB:
################################################################################
if [[ -n "$HL_VER" && "$HL_VER" != "-" && "`python -V 2>&1`" < "Python 2.5" ]]; then
mkdir hashlib
pushd hashlib

(
wget http://code.krypto.org/python/hashlib/hashlib-${HL_VER}.tar.gz && \
tar xvzf hashlib-${HL_VER}.tar.gz && \
cd hashlib-${HL_VER} && \
$PYBIN setup.py build && \
$PYBIN setup.py install
echo $? > ${BEAH_TEMP}/hashlib.rc
) | tee ${BEAH_TEMP}/hashlib.out 2> ${BEAH_TEMP}/hashlib.err

HL_OK=`cat ${BEAH_TEMP}/hashlib.rc`

popd
else
HL_OK=0
fi

################################################################################
# GET BEAKER FROM GIT:
################################################################################
if [[ -n "$BKR" ]]; then
git clone --depth 1 http://git.fedorahosted.org/git/beaker.git
fi


################################################################################
# SUMMARY:
################################################################################
if [[ "$PY_OK" -eq 0 ]]; then
	echo "Python installed OK"
else
	echo "--- ERROR: Python not installed"
fi

if [[ "$ZI_OK" -eq 0 ]]; then
	echo "zope.interface installed OK"
else
	echo "--- ERROR: zope.interface not installed"
fi

if [[ "$TW_OK" -eq 0 ]]; then
	echo "Twisted installed OK"
else
	echo "--- ERROR: Twisted not installed"
fi

if [[ "$ST_OK" -eq 0 ]]; then
	echo "setuptools installed OK"
else
	echo "--- ERROR: setuptools not installed"
fi

if [[ "$SJ_OK" -eq 0 ]]; then
	echo "simplejson installed OK"
else
	echo "--- ERROR: simplejson not installed"
fi

if [[ "$UUID_OK" -eq 0 ]]; then
	echo "uuid installed OK"
else
	echo "--- ERROR: uuid not installed"
fi

if [[ "$HL_OK" -eq 0 ]]; then
	echo "hashlib installed OK"
else
	echo "--- ERROR: hashlib not installed"
fi

if [[ "$GIT_OK" -eq 0 ]]; then
	echo "Git installed OK"
else
	echo "--- ERROR: Git not installed"
fi

################################################################################
popd

)

