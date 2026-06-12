# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


def get(key, default=None):
    from bkr.server.app import app
    return app.config.get(key, default)


def update(values):
    from bkr.server.app import app
    app.config.update(values)
