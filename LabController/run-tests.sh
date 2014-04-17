#/bin/bash
set -x

env PYTHONPATH=src:../Common${PYTHONPATH:+:$PYTHONPATH} \
    nosetests ${*:--v --traverse-namespace bkr.labcontroller}
