#!/usr/bin/python

import datetime
from turbogears.database import session
from bkr.server.util import load_config
from bkr.server.model import System

def check_reservations(system):
    if system.user is not None:
        assert system.reservations[0].finish_time is None
    if not system.reservations: return
    prev = system.reservations[0]
    if prev.finish_time:
        assert prev.start_time <= prev.finish_time, \
                '%r is backwards' % prev
    for r in system.reservations[1:]:
        assert r.finish_time <= prev.start_time, \
                '%r does not finish before %r' % (r, prev)
        assert r.start_time <= r.finish_time, '%r is backwards' % r
        prev = r

if __name__ == '__main__':
    load_config()
    for system_id in [s.id for s in System.query()]:
        system = System.query().get(system_id)
        check_reservations(system)
        session.clear()
