#!/bin/bash

set -x

# if BKR_PY3 is not present and NOT python3
if [[ -z ${BKR_PY3} ]] || [[ ${BKR_PY3} != 1 ]]; then
    test_command="nosetests ${*:--v bkr}";
else
    test_command="pytest-3";
fi

env PYTHONPATH=../Client/src:../Common${PYTHONPATH:+:$PYTHONPATH} ${test_command}

