#/bin/bash

set -x

env PYTHONPATH=.${PYTHONPATH:+:$PYTHONPATH} \
    nosetests ${*:--v bkr}
