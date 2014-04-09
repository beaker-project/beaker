
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
This module is supposed to workaround to support:
- simplejson
- standard library JSON
- python-json
"""

try:
    import json
except ImportError:
    import simplejson as json

try:
    dumps = json.dumps
    loads = json.loads
except AttributeError:
    # Support python-json from EPEL on RHEL5
    # We just silently ignore the pretty-printing arg
    # in this case, since python-json doesn't support it
    def dumps(obj, indent=None):
        return json.write(obj)

    def loads(obj):
        return json.read(obj)
