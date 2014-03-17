#/bin/bash

set -x

env PYTHONPATH=../Client/src:../Common${PYTHONPATH:+:$PYTHONPATH} \
    nosetests ${*:--v --traverse-namespace bkr.client.tests}
