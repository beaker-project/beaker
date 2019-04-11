#/bin/bash

set -x

# Use Python 2 version if BKR_PY3 is not defined
if [[ -z ${BKR_PY3} ]]; then
    nose_command="nosetests";
elif [[ ${BKR_PY3} == 1 ]]; then
    nose_command="nosetests-3";
else
    nose_command="nosetests";
fi

env PYTHONPATH=.${PYTHONPATH:+:$PYTHONPATH} \
    $nose_command ${*:--v bkr}
