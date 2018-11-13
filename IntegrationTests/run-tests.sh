#!/bin/bash

# Beaker's tests are spread across several places. Unit tests live beside the 
# code they are testing, usually in a module named test_*.py. Integration 
# tests, which depend on external resources (such as databases) and create new 
# processes and are generally expensive, live here under IntegrationTests.
#
# This is a convenience script to run all tests in one go from a Beaker source 
# checkout, without building anything.

if [ $(pwd) != $(readlink -f $(dirname "$0") ) ] ; then
    # Unfortunately there is at least one place in tests where we are sensitive 
    # to cwd (beaker.motd in server-test.cfg) :-(
    echo "Run this script from the IntegrationTests directory" >&2
    exit 1
fi

set -x

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
#
# We need to set BEAKER_CONFIG_FILE here, so that our unit tests in bkr.server don't try and
# load their own config (subsequent calls to update_config() don't seem to work...)
env BEAKER_CONFIG_FILE='server-test.cfg' \
    DISCARD_SUBPROCESS_OUTPUT=${DISCARD_SUBPROCESS_OUTPUT:-0} \
    PYTHONPATH=../Common:../Server:../LabController/src:../Client/src:../IntegrationTests/src${PYTHONPATH:+:$PYTHONPATH} \
    python2 -c '__requires__ = ["CherryPy < 3.0", "Jinja2 >= 2.6"]; import pkg_resources; from nose.core import main; main()' \
    ${*:--v bkr.inttest}
