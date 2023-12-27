#!/bin/bash

set -x

# Use nosetests with python2 interpreter
if [[ -z ${BKR_PY3} ]] || [[ ${BKR_PY3} != 1 ]]; then
    command="nosetests ${*:--v bkr}";
else
    command="pytest-3";
fi

env PYTHONPATH=../Client/src:../Common${PYTHONPATH:+:$PYTHONPATH} $command
