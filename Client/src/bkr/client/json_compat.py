# This module is supposed to workaround to support:
# - simplejson
# - standard library JSON
# - python-json

try:
    import json
except ImportError:
    import simplejson as json

try:
    dumps = json.dumps
except AttributeError:
    # Support python-json from EPEL on RHEL5
    # We just silently ignore the pretty-printing arg
    # in this case, since python-json doesn't support it
    def dumps(obj, indent=None):
        return json.write(obj)
