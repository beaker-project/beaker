#!/bin/bash

# see run-client.sh. Used to run the wizard directly from a source checkout.
exec env PYTHONPATH=$(dirname "$0")/../Common:$(dirname "$0")/../Client/src${PYTHONPATH:+:$PYTHONPATH} \
    python2 -u $(dirname "$0")/../Client/src/bkr/client/wizard.py "$@"
