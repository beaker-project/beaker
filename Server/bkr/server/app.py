
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from flask import Flask, send_from_directory
from turbogears import config
import turbojson.jsonify

# This is NOT the right way to do this, we should just use SCRIPT_NAME properly instead.
# But this is needed to line up with TurboGears server.webpath way of doing things.
class PrefixedFlask(Flask):
    def add_url_rule(self, rule, *args, **kwargs):
        prefixed_rule = config.get('server.webpath', '').rstrip('/') + rule
        return super(PrefixedFlask, self).add_url_rule(prefixed_rule, *args, **kwargs)

app = PrefixedFlask('bkr.server')

# Make flask.jsonify use TurboJson
app.json_encoder = turbojson.jsonify.GenericJSON

# URL rules for serving static assets. The same URL paths are mapped in the 
# Apache config, so in production the Python application will never see these 
# requests at all. This is just for the development server.

@app.route('/assets/generated/<path:filename>')
def assets_generated(filename):
    return send_from_directory(
            os.path.abspath(config.get('basepath.assets_cache')),
            filename)

@app.route('/assets/<path:filename>')
def assets(filename):
    return send_from_directory(
            os.path.abspath(config.get('basepath.assets')),
            filename)
