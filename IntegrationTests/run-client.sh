#!/bin/bash

# Just a wrapper to run bkr client directly from a source checkout, without 
# building or installing anything. Used by integration tests.

if [[ ${BKR_PY3} == 1 ]]; then
    python=python3
else
    python=python2
fi

exec env PYTHONPATH=$(dirname "$0")/../Common:$(dirname "$0")/../Client/src${PYTHONPATH:+:$PYTHONPATH} \
    $python -u $(dirname "$0")/../Client/src/bkr/client/main.py "$@"
