#!/bin/bash

# Just a wrapper to run bkr client directly from a source checkout, without 
# building or installing anything. Used by integration tests.

exec env PYTHONPATH=$(dirname "$0")/../Common:$(dirname "$0")/../Client/src${PYTHONPATH:+:$PYTHONPATH} \
    python2 -u $(dirname "$0")/../Client/src/bkr/client/main.py "$@"
