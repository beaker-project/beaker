#!/bin/bash

# see run-client.sh. Used to run the wizard directly from a source checkout.
if [[ ${BKR_PY3} == 1 ]]; then
    python=python3
else
    python=python2
fi

exec env PYTHONPATH=$(dirname "$0")/../Common:$(dirname "$0")/../Client/src${PYTHONPATH:+:$PYTHONPATH} \
    $python -u $(dirname "$0")/../Client/src/bkr/client/wizard.py "$@"
