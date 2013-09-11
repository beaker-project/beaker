# Run this as Misc/run-pylint.sh from the base of a working copy

export PYTHONPATH=Common:Server:LabController/src:Client/src:IntegrationTests/src${PYTHONPATH:+:$PYTHONPATH}
pylint --rcfile=Misc/pylint-errors.cfg $*
