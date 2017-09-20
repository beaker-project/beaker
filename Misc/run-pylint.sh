# Run this from the base of a working copy, for example:
#   Misc/run-pylint.sh -E bkr

# On Fedora 26+, /usr/bin/pylint is Python 3 and /usr/bin/pylint-2 is Python 2.
# On RHEL 6 there is only /usr/bin/pylint (Python 2).
if command -v pylint-2 >/dev/null ; then
    PYLINT=pylint-2
else
    PYLINT=pylint
fi

# Add Beaker source code to PYTHONPATH
PYTHONPATH=Common:Server:LabController/src:Client/src:IntegrationTests/src${PYTHONPATH:+:$PYTHONPATH}
export PYTHONPATH

# For Beaker Pylint plugin
PYTHONPATH=Misc:$PYTHONPATH
PYLINT_PLUGINS=pylint_beaker

$PYLINT --rcfile=Misc/pylint-errors.cfg --load-plugins=$PYLINT_PLUGINS "$@"
