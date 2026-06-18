
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import timedelta
from bkr.server import identity
from bkr.server.model import Watchdog
from bkr.server.rpc import expose, register


@register('watchdogs')
class Watchdogs(object):
    # For XMLRPC methods in this class.
    exposed = True

    # TODO: future cleanup so that the correct error message
    # is given to the client code.
    @identity.require(identity.in_group('admin'))
    @expose
    def extend(self, time):
        '''Allow admins to push watchdog times out after an outage'''

        watchdogs = []
        for w in Watchdog.by_status(status=u'active'):
            n_kill_time = w.kill_time + timedelta(seconds=time)
            watchdogs.append("R:%s watchdog moved from %s to %s" % (
                              w.recipe_id, w.kill_time, n_kill_time))
            w.kill_time = n_kill_time

        if watchdogs:
            return "\n".join(watchdogs)
        else:
            return 'No active watchdogs found'
