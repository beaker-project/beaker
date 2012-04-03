__all__ = [ "BeakerBus", "VALID_AMQP_TYPES"]

import ConfigParser, os
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
    _reconnect = True
    _reconnect_interval = 5
    _auth_mgr = None
    _fetch_timeout=60
    _auth_interval = 3600 * 4 # Four hours


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

    def get_qpid_connection(self):
        global can_use_qpid, _connection
        if not can_use_qpid:
            global qpid_import_error
            raise ImportError(str(qpid_import_error))
        if _connection is None:
            connection_params = [[self._broker], {'reconnect' : self._reconnect, 'reconnect_interval' : self._reconnect_interval, 'reconnect_timeout' :10 }]
            if self.krb_auth:
                connection_params[1].update({'sasl_mechanisms' : 'GSSAPI'})
                self.do_krb_auth()
                # krb auths have a set lifespan, ensure we stay authenticated
                RepeatTimer(self._auth_interval, self.do_krb_auth, stop_on_exception=False)
            _connection = Connection(*connection_params[0], **connection_params[1])
            try:
                _connection.open()
            except Exception, e:
                _connection = None
                raise
        return _connection

    def __init__(self, connection=None, *args, **kw):
        if connection is None:
            connection = self.get_qpid_connection()
        self.conn = connection
        self.thread_handlers = {}
        self.rpc = self.RPCInterface(self)

    def service_queue_sender(self, session, method, *args):
        reply_to_queue_name = 'tmp.beaker-receive' + str(datatypes.uuid4())
        reply_to_addr_string = reply_to_queue_name +'; { create:receiver, \
                node: { type: queue, durable:False, \
                x-declare: {exclusive: True, auto-delete:True, \
                            arguments: { \'qpid.policy_type\': ring, \
                                         \'qpid.max_size\': 50000000 } }, \
                x-bindings: [{ exchange: "' + self.direct_exchange + '", \
                               key: "' + reply_to_queue_name + '", \
                               queue: "' + reply_to_queue_name + '", } ] } }'
        new_receiver = session.receiver(reply_to_addr_string)
        msg = Message(reply_to=reply_to_queue_name)
        msg.properties['method'] = method
        msg.properties['args'] = args
        msg.subject = self.service_queue_name
        snd = session.sender(self.direct_exchange)
        snd.send(msg)
        log.debug('sent %s on to %s' % (msg, self.service_queue_name))
        try:
            message_response = new_receiver.fetch(timeout=self._fetch_timeout)
        except exceptions.Empty:
            session.close()
            raise Exception('Timeout waiting to receive response from broker')

        session.close()
        if message_response.properties.get('error'):
            raise Exception(message_response.content)
        return message_response.content

    def send_action(self, method_name, *args, **kw):
        log.debug('In send_action')
        send_action = getattr(self, '%s_sender' % method_name, None)
        if send_action is None:
            raise BeakerException(u'%s is not a valid send handler' % method_name)
        new_session = self.conn.session()
        log.debug('Calling %s from send_action' % send_action)
        return send_action(new_session, *args, **kw)

    def listen_action(self, method_name, **args):
        listen_action = getattr(self, '%s_listener' % method_name, None)
        if listen_action is None:
            raise BeakerException(u'%s is not a valid listen handler' % method_name)
        new_session = self.conn.session()
        listen_action(new_session, *args)


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



