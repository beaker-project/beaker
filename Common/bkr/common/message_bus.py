from qpid.messaging import *
from qpid.log import enable, DEBUG, WARN, ERROR
from qpid import datatypes
enable("qpid.messaging", ERROR)
import ConfigParser, os

class BeakerBus(object):

    _reconnect = True
    _reconnect_interval = 3
    _arg_index = 0
    _kw_index = 1
    _shared_dict = {}

    default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "message_bus.conf"))
    config = ConfigParser.ConfigParser()
    config.readfp(open(default_config))
    _broker = config.get('global','broker')
    headers_exchange = config.get('global', 'headers_exchange')
    topic_exchange = config.get('global', 'topic_exchange')
    service_queue_name = config.get('global', 'service_queue')


    class ListenHandlers(object):
        pass


    class SendHandlers(object):


        error_suffix = 'Cannot send message'
    
        def __init__(self, *args, **kw):
            pass

        @classmethod
        def service_queue(cls, session, method, *args):
            #FIXME add exception handling
            reply_to_queue_name = 'tmp.beaker-receive' + str(datatypes.uuid4())
            reply_to_addr_string = reply_to_queue_name +'; { create:receiver, \
                node: { type: queue, durable:False, \
                x-declare: {exclusive: True, auto-delete:True } } }'
            new_receiver = session.receiver(reply_to_addr_string)
            msg = Message(reply_to=reply_to_queue_name)
            msg.properties['method'] = method
            msg.properties['args'] = args
            service_queue_name = BeakerBus().service_queue_name
            snd = session.sender(service_queue_name)
            snd.send(msg)
            message_response = new_receiver.fetch(timeout=10)
            session.close()
            if message_response.properties.get('error'):
                raise Exception(message_response.content)
            return message_response.content


    def __init__(self, *args, **kw):
        if self._shared_dict:
            self.__dict__ = self._shared_dict
        else:
            connection_params = [[self._broker], {'reconnect' : self._reconnect, 'reconnect_interval' : self._reconnect_interval, }]
            #FIXME add this back in for production
            #connection_params[self._kw_index].update({'sasl_mechanisms' : 'GSSAPI'})
            self._shared_dict['conn'] = Connection(*connection_params[self._arg_index],**connection_params[self._kw_index])
            self._shared_dict['conn'].open()
            self._shared_dict['thread_handlers'] = {}
            self.__dict__ = self._shared_dict

    def send_action(self, method_name, *args):
        send_action = getattr(self.SendHandlers, method_name, None)
        if send_action is None:
            return BeakerException(_('%s is not a valid handler' % method_name))
        new_session = self.conn.session()
        return send_action(new_session, *args)

    def listen_action(self, method_name, **args):
        send_action = getattr(ListenHandlers, method_name, None)
        if send_action is None:
            return BeakerException(_('%s is not a valid handler' % method_name))
        self._open_connection()
        new_session = self.conn.session()
        listen_action(new_session, *args)


    def run(self, *args, **kw):
        raise NotImplementedError('class %s must implement run() method' % self.__class__.__name__)

    def _open_connection(self, *args, **kw):
        try:
            self.conn.open()
        except ConnectionError, e:
            if 'already open' in str(e):
                pass
            else:
                raise


