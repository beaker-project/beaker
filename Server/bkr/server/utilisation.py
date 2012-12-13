
import datetime
from sqlalchemy.sql import and_, or_, func
from turbogears.database import session
from bkr.server.model import System, SystemStatusDuration, Reservation

def update_status_durations_in_period(tally, status_durations, start, end):
    for sd in status_durations:
        if sd.start_time < end and (sd.finish_time or end) > start:
            duration = min(sd.finish_time or end, end) - max(sd.start_time, start)
            assert duration >= datetime.timedelta(0)
            tally['idle_%s' % sd.status.value.lower()] += duration

def system_utilisation(system, start, end):
    retval = dict((k, datetime.timedelta(0)) for k in
            ['recipe', 'manual', 'idle_automated', 'idle_manual',
             'idle_broken', 'idle_removed'])
    if end <= system.date_added:
        return retval
    if start <= system.date_added:
        start = system.date_added
    status_durations = system.dyn_status_durations\
            .filter(and_(SystemStatusDuration.start_time < end,
                or_(SystemStatusDuration.finish_time >= start,
                    SystemStatusDuration.finish_time == None)))\
            .order_by(SystemStatusDuration.start_time).all()
    reservations = system.dyn_reservations\
            .filter(and_(Reservation.start_time < end,
                or_(Reservation.finish_time >= start,
                    Reservation.finish_time == None)))\
            .order_by(Reservation.start_time).all()
    prev_finish = start
    for reservation in reservations:
        # clamp reservation start and finish to be within the period
        clamped_res_start = max(reservation.start_time, start)
        clamped_res_finish = min(reservation.finish_time or end, end)
        # first, do the gap from the end of the previous reservation to the 
        # start of this one
        update_status_durations_in_period(retval, status_durations,
                prev_finish, clamped_res_start)
        # now do this actual reservation
        retval[reservation.type] += clamped_res_finish - clamped_res_start
        prev_finish = clamped_res_finish
    # lastly, do the gap from the end of the last reservation to the end of the 
    # reporting period
    update_status_durations_in_period(retval, status_durations,
            prev_finish, end)
    return retval

def system_utilisation_counts(systems):
    """
    Similar to the above except returns counts of systems based on the current 
    state, rather than historical data about particular systems.
    """
    retval = dict((k, 0) for k in
            ['recipe', 'manual', 'idle_automated', 'idle_manual',
             'idle_broken', 'idle_removed'])
    query = systems.outerjoin(System.open_reservation)\
            .with_entities(func.coalesce(Reservation.type,
                func.concat('idle_', func.lower(System.status))),
                func.count(System.id))\
            .group_by(1)
    for state, count in query:
        retval[state] = count
    return retval
