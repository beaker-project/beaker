
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import turbogears
from turbojson import jsonify
import bkr.common
from bkr.server import identity

def jsonify_for_html(obj):
    json = jsonify.encode(obj)
    # "</script>" can appear in a JSON string but must not appear inside 
    # a <script> tag with HTML doctype
    json = json.replace('</', r'\u003c\u002f')
    # U+2028 and U+2029 are legal in JSON strings but not in JavaScript string 
    # literals: http://timelessrepo.com/json-isnt-a-javascript-subset
    json = json.replace(u'\u2028', r'\u2028').replace(u'\u2029', r'\u2029')
    return json

def beaker_version():
   try: 
        return bkr.common.__version__
   except AttributeError, (e): 
        return 'devel-version'   

def add_custom_stdvars(vars):
    return vars.update({
        "beaker_version": beaker_version,
        "identity": identity.current, # well that's just confusing
        "to_json": jsonify_for_html,
    })

turbogears.view.variable_providers.append(add_custom_stdvars)

