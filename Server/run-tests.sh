#/bin/bash

set -x

env PYTHONPATH=../Server:../Common${PYTHONPATH:+:$PYTHONPATH} \
    python -c '__requires__ = ["CherryPy < 3.0"]; import pkg_resources; from nose.core import main; main()' \
    ${*:--v --traverse-namespace bkr.server.tests}
