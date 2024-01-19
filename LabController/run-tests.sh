#!/bin/bash
set -x

# Use nosetests with python2 interpreter
if [[ -z ${BKR_PY3} ]] || [[ ${BKR_PY3} != 1 ]]; then
    command="nosetests ${*:--v --traverse-namespace bkr.labcontroller}";
else
    # Check if pytest-3 is available
    if command -v pytest-3 >/dev/null 2>&1; then
        command="pytest-3";
    else
        command="pytest";
    fi
fi

env PYTHONPATH=src:../Common${PYTHONPATH:+:$PYTHONPATH} $command
