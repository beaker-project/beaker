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

# If you want to run unittests for beaker client, in your env set BEAKER_CLIENT_TEST_QPID=1,
# and also set BEAKER_CLIENT_TEST_QPID_BROKER to something reasonable.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)

env PYTHONPATH=../Common:../Server:../LabController/src:../Client/src:../IntegrationTests/src${PYTHONPATH:+:$PYTHONPATH} \
    python -c '__requires__ = ["CherryPy < 3.0"]; import pkg_resources; from nose.core import main; main()' \
    ${*:--v rhts bkr}
