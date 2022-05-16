#!/bin/bash

set -x

# Use Python 2 version if BKR_PY3 is not defined
if [[ -z ${BKR_PY3} ]]; then
    pytest_command="py.test-2";
elif [[ ${BKR_PY3} == 1 ]]; then
    pytest_command="pytest-3";
else
    pytest_command="py.test-2";
fi

env PYTHONPATH=../Client/src:../Common${PYTHONPATH:+:$PYTHONPATH} \
    $pytest_command
