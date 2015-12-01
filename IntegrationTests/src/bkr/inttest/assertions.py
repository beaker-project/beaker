
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import difflib
import time
import datetime

def assert_sorted(things, key=None):
    """
    Asserts that the given sequence is in sorted order.
    """
    if len(things) == 0: return
    if key is not None:
        things = map(key, things)
    for n in xrange(1, len(things)):
        if things[n] < things[n - 1]:
            raise AssertionError('Not in sorted order, found %r after %r' %
                    (things[n], things[n - 1]))

def assert_has_key_with_value(system, key_name, value):
    for kv in system.key_values_int:
        if kv.key.key_name == key_name and kv.key_value == value:
            return
    for kv in system.key_values_string:
        if kv.key.key_name == key_name and kv.key_value == value:
            return
    raise AssertionError('No such key with name %r and value %r found on system %r'
            % (key_name, value, system))

def assert_datetime_within(dt, tolerance, reference=None):
    """
    Asserts that the given datetime is within tolerance of reference. By 
    default, the reference point is now.

    :type dt: datetime.datetime
    :type tolerance: datetime.timedelta
    :type reference: datetime.datetime
    """
    if reference is None:
        reference = datetime.datetime.now()
    if abs(reference - dt) > tolerance:
        raise AssertionError('%r is not within %r of reference %r'
                % (dt, tolerance, reference))

def assert_durations_not_overlapping(durations):
    """
    Given an iterable of anything with start_time and finish_time attributes, 
    asserts that there are no overlaps in the durations.
    """
    # XXX this is inefficient, only suitable for small collections
    seen_durations = []
    for duration in durations:
        # the start time must not be enclosed by any duration which 
        # we have already seen
        for seen in seen_durations:
            if duration.start_time >= seen.start_time \
                    and (seen.finish_time is None
                         or duration.start_time < seen.finish_time):
                raise AssertionError('%r overlaps with %r' % (duration, seen))
        seen_durations.append(duration)

def assert_durations_contiguous(durations):
    durations = sorted(durations, key=lambda d: d.start_time)
    for i in range(1, len(durations)):
        if durations[i - 1].finish_time != durations[i].start_time:
            raise AssertionError('Gap found between %r and %r'
                    % (durations[i - 1], durations[i]))

def wait_for_condition(condition_func, timeout=30):
    start_time = time.time()
    while True:
        if condition_func():
            break
        if time.time() - start_time > timeout:
            raise AssertionError('Condition %r not satisfied within %d seconds'
                    % (condition_func, timeout))
        else:
            time.sleep(0.25)

def character_diff_message(expected, actual):
    """Creates a character diff comparing the two strings. Can be used as a
    message for a test assertion."""
    diffed = ''.join(difflib.unified_diff(list(expected), list(actual), n=10))
    return 'Diff:\n %s\nExpected:\n %s\nActual:\n %s' % (diffed, expected, actual)
