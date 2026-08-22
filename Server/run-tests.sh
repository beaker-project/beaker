#/bin/bash

set -x

if [[ -z ${BKR_PY3} ]] || [[ ${BKR_PY3} != 1 ]]; then
    env BEAKER_CONFIG_FILE='bkr/server/tests/unit-test.cfg' PYTHONPATH=../Server:../Common${PYTHONPATH:+:$PYTHONPATH} \
        python2 -c '__requires__ = ["CherryPy < 3.0"]; import pkg_resources; from nose.core import main; main()' \
        ${*:--v --traverse-namespace bkr.server.tests}
else
    if command -v pytest-3 >/dev/null 2>&1; then
        pytest=pytest-3
    else
        pytest=pytest
    fi
    env BEAKER_CONFIG_FILE='bkr/server/tests/unit-test.cfg' \
        PYTHONPATH=../Server:../Common${PYTHONPATH:+:$PYTHONPATH} \
        $pytest --pyargs ${*:--v bkr.server.tests}
fi
