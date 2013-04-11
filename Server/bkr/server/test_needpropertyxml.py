
import unittest
from bkr.server import needpropertyxml

decimal_prefixes = {
    'k': 10**3,
    'K': 10**3,
    'M': 10**6,
    'G': 10**9,
    'T': 10**12,
}
binary_prefixes = {
    'Ki': 2**10,
    'Mi': 2**20,
    'Gi': 2**30,
    'Ti': 2**40,
}

def test_bytes_multiplier():
    yield check_bytes_multiplier, 'bytes', 1
    yield check_bytes_multiplier, 'B', 1
    for prefix, multiplier in decimal_prefixes.iteritems():
        yield check_bytes_multiplier, prefix + 'B', multiplier
    for prefix, multiplier in binary_prefixes.iteritems():
        yield check_bytes_multiplier, prefix + 'B', multiplier

def check_bytes_multiplier(units, expected):
    actual = needpropertyxml.bytes_multiplier(units)
    assert actual == expected, 'Units %s, expected %s, actual %s' % (
            units, expected, actual)
