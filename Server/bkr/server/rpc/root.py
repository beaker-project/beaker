
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import LabController
from bkr.server.rpc import expose, register


@register('')
class Root(object):
    exposed = True

    @expose
    def lab_controllers(self):
        query = LabController.query.filter(LabController.removed == None)
        return [lc.fqdn for lc in query]
