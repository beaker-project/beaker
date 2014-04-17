
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

__all__ = [ "BeakerBus"]

import ConfigParser
import os
import Queue
import socket
from threading import Lock 
from time import sleep
from bkr.common.helpers import curry, RepeatTimer
from bkr.common.bexceptions import BeakerException

can_use_qpid = True
try:
    from qpid.messaging import exceptions, Connection, MessagingError
    from qpid.log import enable, DEBUG, WARN, ERROR
    from qpid import datatypes
    enable("qpid.messaging", ERROR)
except ImportError, e:
    can_use_qpid = False
    qpid_import_error = e

import logging
log = logging.getLogger(__name__)

_connection = None


class BeakerBus(object):

    # XXX Config file ?
    _reconnect = False
    _fetch_timeout = 60
    _broker = None
    _reconnect_interval = 10
    _connection_attempts = 10
    _heartbeat_timeout = 60
    connection_lock = Lock()


    def do_krb_auth(self):
        raise NotImplementedError('Configured to use kerberos auth '
                'but not implemented by class %s' % self.__class__.__name__)

    def _manage_initial_connection(self):
        """Connect to a broker, return connection object.

        Handles  limited number of connect errors on the initial connect
        before giving up.

        """
        tried = 0
        while True:
            try:
                return self.get_qpid_connection()
            except exceptions.ConnectError, e:
                tried = tried + 1
                if tried >= self._connection_attempts:
                    raise
                else:
                    sleep(self._reconnect_interval)
                    log.debug('Attempting to connect after: %s' % str(e))

    def get_qpid_connection(self):
        """Connect to a broker, set and  return the connection object

        Authenticates (if necessary), and sets bkr.common._connection and
        returns it. This method is thread safe.

        """
        self.connection_lock.acquire()
        try:
            global can_use_qpid, _connection
            if not can_use_qpid:
                global qpid_import_error
                raise ImportError(str(qpid_import_error))
            if _connection is None or _connection.get_error():
                connection_params = [[self._broker],
                                     {'reconnect': self._reconnect,
                                      'heartbeat': self._heartbeat_timeout}]
                if self.krb_auth:
                    connection_params[1].update({'sasl_mechanisms' : 'GSSAPI'})
                    # As connections can recover from krb errors, we don't need
                    # to worry about doing this manually.
                    self.do_krb_auth()
                _connection = Connection(*connection_params[0], **connection_params[1])
                _connection.open()
            return _connection
        finally:
            self.connection_lock.release()

    def __init__(self, connection=None, krb=False, *args, **kw):
        if krb:
            self.krb_auth = True
            self.principal = kw.get('principal', None)
            self.keytab = kw.get('keytab', None)
        else:
            self.krb_auth = False
        if connection is None:
            connection = self._manage_initial_connection()
        self.stopped = False
        self.conn = connection

    def stop(self):
        log.debug('%s is stopping' % self.__class__.__name__)
        self.stopped = True
        self.cleanup()

    def cleanup(self):
        log.debug('%s is cleaning up' % self.__class__.__name__)
        self.conn.close()
        log.debug('%s has cleaned up' % self.__class__.__name__)

    def _manage_connection(self, action, ssn):
        local_ssn = ssn[0]
        while True:
            try:
                return action(local_ssn)
            except (MessagingError,
                exceptions.ConnectionError), e:
                log.debug("Attempting to recover from '%s' in %s" % (str(e), action.__name__))
                # Either the connection or the session is the culprit
                if self.conn.get_error():
                    log.debug('Connection error')
                    try:
                        self.conn = self.get_qpid_connection()
                    # ConnectError will be thrown if we can't reach the service
                    # or if we can't Authenticate due to expired ticket
                    except exceptions.ConnectError:
                        # The connection is still not up
                        sleep(10)
                elif local_ssn.get_error():
                    log.debug('Session error')
                    ssn[0] = local_ssn = self.conn.session()
                else:
                    raise # What else could it be ?

    def fetch(self, ssn, addr, *args, **kw):

        def _fetch(local_ssn):
            receiver = local_ssn.receiver(addr)
            while True:
                try:
                    msg = receiver.fetch(*args, **kw)
                    log.debug('Received message: %s' % msg)
                    return msg
                except exceptions.Empty:
                    log.debug('Timeout waiting to fetch ' 
                        'message from address: %s' % addr)
                    return None

        return self._manage_connection(_fetch, ssn)

    def send(self, ssn, exchange, msg, *args, **kw):

        def _send(local_ssn):
            snd = local_ssn.sender(exchange)
            snd.send(msg)
            log.debug('Sent %s to exchange %s' % (msg, exchange))

        self._manage_connection(_send, ssn)

    def run(self, *args, **kw):
        raise NotImplementedError('class %s must implement run() method' % self.__class__.__name__)

