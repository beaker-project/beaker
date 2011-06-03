#!/usr/bin/python

import datetime
from sqlalchemy import and_
from turbogears.database import session
from bkr.server.util import load_config
from bkr.server.model import System, SystemStatus, SystemActivity, \
        SystemStatusDuration
from bkr.server.test.assertions import assert_durations_not_overlapping, \
        assert_durations_contiguous

def get_status(value):
    if value == u'Working':
        value = u'Automated'
    try:
        return SystemStatus.by_id(int(value))
    except ValueError:
        return SystemStatus.by_name(value)

def populate_status_durations(system):
    assert not system.status_durations
    # We don't know what the original status was, so let's set it to None for 
    # now and see if we can figure it out next
    start_time = system.date_added
    status = None
    for activity in SystemActivity.query().filter(and_(
            SystemActivity.object == system,
            SystemActivity.field_name.in_([u'Status', u'status_id']),
            SystemActivity.action == u'Changed'))\
            .order_by(SystemActivity.created):
        # Some old records have activity before date_added, probably because 
        # the former is not in UTC
        changed_at = max(system.date_added, activity.created)
        # If this is the first status change, old_value might tell us what it 
        # was before
        if status is None:
            if activity.old_value:
                status = get_status(activity.old_value)
            else:
                # As a fallback, assume systems always started out broken
                status = get_status(u'Broken')
        new_status = get_status(activity.new_value)
        # If the duration was non-zero, let's record it
        if changed_at > start_time and status != new_status:
            system.status_durations.append(SystemStatusDuration(
                    status=status, start_time=start_time, finish_time=changed_at))
            status = new_status
            start_time = changed_at
    if status is None:
        status = get_status(u'Broken')
    system.status_durations.append(SystemStatusDuration(
            status=status, start_time=start_time, finish_time=None))
    assert_durations_not_overlapping(system.status_durations)
    assert_durations_contiguous(system.status_durations)
    assert system.date_added == system.status_durations[0].start_time

if __name__ == '__main__':
    load_config()
    session.begin()
    for system_id in [s.id for s in System.query()]:
        system = System.query().get(system_id)
        populate_status_durations(system)
        session.flush()
        session.clear()
    session.commit()
