#/bin/bash

set -x

env BEAKER_CONFIG_FILE='bkr/server/tests/unit-test.cfg' PYTHONPATH=../Server:../Common${PYTHONPATH:+:$PYTHONPATH} \
    python2 -c '__requires__ = ["CherryPy < 3.0"]; import pkg_resources; from nose.core import main; main()' \
    ${*:--v --traverse-namespace bkr.server.tests}
