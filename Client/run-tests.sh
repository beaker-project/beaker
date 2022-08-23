#/bin/bash

set -x

# if BKR_PY3 is present and defined use pytest-3
if [[ ! -z ${BKR_PY3} ]] && [[ ${BKR_PY3} == 1 ]]; then
    test_command="pytest-3";
else
    test_command="nosetests ${*:--v --traverse-namespace bkr.client.tests}";
fi

env PYTHONPATH=../Client/src:../Common${PYTHONPATH:+:$PYTHONPATH} \
    $test_command
