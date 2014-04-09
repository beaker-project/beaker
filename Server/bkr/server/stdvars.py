
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import turbogears
from turbojson import jsonify
import bkr.common
from bkr.server import identity

def beaker_version():
   try: 
        return bkr.common.__version__
   except AttributeError, (e): 
        return 'devel-version'   

def add_custom_stdvars(vars):
    return vars.update({
        "beaker_version": beaker_version,
        "identity": identity.current, # well that's just confusing
        "to_json": jsonify.encode,
    })

turbogears.view.variable_providers.append(add_custom_stdvars)

