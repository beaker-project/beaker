__all__ = [ "BeakerBus", "VALID_AMQP_TYPES"]

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
    from qpid.messaging import *
    from qpid.log import enable, DEBUG, WARN, ERROR
    from qpid import datatypes
    enable("qpid.messaging", ERROR)
except ImportError, e:
    can_use_qpid = False
    qpid_import_error = e

import logging
log = logging.getLogger(__name__)

VALID_AMQP_TYPES=[list,dict,bool,int,long,float,unicode,dict,list,str,type(None)]
_connection = None


class BeakerBus(object):

    # XXX Config file ?
    _reconnect = False
    _auth_mgr = None
    _fetch_timeout = 60
    _broker = None
    _reconnect_interval = 10
    _connection_attempts = 10
    _heartbeat_timeout = 60
    connection_lock = Lock()


    class RPCInterface:

        """ Provides a way of calling RPC as attributes
        """

        def __init__(self, bus, *args, **kw):
            if  not isinstance(bus,BeakerBus):
                raise TypeError('%s can only be used with %s, not %s' % \
                    (self.__class__.__name__, BeakerBus.__name__, bus.__class__.__name__))
            self.bus = bus

        def __getattr__(self, name):
            return _Method(curry(self.bus.send_action, 'service_queue'), name)

        def __repr__(self):
            return (
                "<BeakerBusRPC for %s:%s>" %
                (self.bus._broker, self.bus.service_queue_name))

        __str__ = __repr__


    @classmethod
    def do_krb_auth(self):
        raise NotImplementedError('Configured to use kerberos auth but not implemented by class %s' % self.__name__)

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

    def __init__(self, connection=None, *args, **kw):
        if connection is None:
            connection = self._manage_initial_connection()
        self.conn = connection
        self.rpc = self.RPCInterface(self)

    def service_queue_sender(self, session, method, *args):
        reply_to_queue_name = 'tmp.beaker-receive' + str(datatypes.uuid4())
        reply_to_addr_string = reply_to_queue_name +'; { create:receiver, \
                node: { type: queue, durable:False, \
                x-declare: {exclusive: True, auto-delete:True, \
                            arguments: { \'qpid.policy_type\': ring, \
                                         \'qpid.max_size\': 50000000, \
                                         \'qpid.last_value_queue\': 1 } }, \
                x-bindings: [{ exchange: "' + self.direct_exchange + '", \
                               key: "' + reply_to_queue_name + '", \
                               queue: "' + reply_to_queue_name + '", } ] } }'
        msg = Message(reply_to=reply_to_queue_name)
        msg.properties['method'] = method
        msg.properties['args'] = args
        msg.subject = self.service_queue_name
        msg.properties['qpid.LVQ_key'] = str(datatypes.uuid4())
        while True:
            self.send(session, self.direct_exchange, msg)
            message_response = self.fetch(session,
                                          reply_to_addr_string,
                                          timeout=self._fetch_timeout)
            if message_response is None:
                log.debug('Try send/receive pattern again')
                continue
            if message_response.properties.get('error'):
                raise BeakerException(message_response.content)
            return message_response.content

    def send_action(self, method_name, *args, **kw):
        log.debug('In send_action')
        send_action = getattr(self, '%s_sender' % method_name, None)
        if send_action is None:
            raise BeakerException(u'%s is not a valid send handler' % method_name)

        new_session = [self.conn.session()]
        try:
            log.debug('Calling %s from send_action' % send_action)
            response = send_action(new_session, *args, **kw)
            return response
        finally:
            new_session[0].close()

    def listen_action(self, method_name, **args):
        listen_action = getattr(self, '%s_listener' % method_name, None)
        if listen_action is None:
            raise BeakerException(u'%s is not a valid listen handler' % method_name)
        new_session = [self.conn.session()]
        try:
            listen_action(new_session, *args)
        finally:
            new_session[0].close()

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


class _Method:


    """A class that enables RPCs to be accessed as attributes ala xmlrpclib.ServerProxy
       Inspired/ripped from xmlrpclib.ServerProxy
    """

    def __init__(self, send, name):
        self.__send = send
        self.__name = name

    def __getattr__(self, name):
        return _Method(self.__send, "%s.%s" % (self.__name, name))

    def __call__(self, *args):
        return self.__send(self.__name, *args)



