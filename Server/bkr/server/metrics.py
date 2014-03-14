
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Routines for sending Beaker metrics to Graphite.
"""

import socket
import time
import logging
from turbogears import config

log = logging.getLogger(__name__)

class CarbonSender(object):

    def __init__(self, address, prefix):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.address = address
        self.prefix = prefix

    def send(self, name, value, timestamp):
        try:
            msg = '%s%s %s %s' % (self.prefix, name, value, timestamp)
            self.sock.sendto(msg, self.address)
        except socket.error:
            log.exception('Error writing to carbon')

_carbon = None
def get_carbon():
    global _carbon
    if _carbon is not None:
        return _carbon
    _carbon = CarbonSender(config.get('carbon.address'),
            config.get('carbon.prefix', 'beaker.'))
    return _carbon

def increment(name):
    if not config.get('carbon.address'):
        return
    carbon = get_carbon()
    carbon.send(name, 1, int(time.time()))

def measure(name, value):
    if not config.get('carbon.address'):
        return
    if not isinstance(value, (long, int, float)):
        raise TypeError('value %r should be a number' % value)
    carbon = get_carbon()
    carbon.send(name, value, int(time.time()))
