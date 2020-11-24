# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Sending messages to the AMQ
"""

import json
import logging
import random

try:
    from proton import Message, SSLDomain
    from proton.handlers import MessagingHandler
    from proton.reactor import Container
    has_proton = True
except ImportError:
    has_proton = False
    MessagingHandler = object

# XXX replace turbogears with beaker prefixed flask when migration is done
from turbogears.config import get

log = logging.getLogger(__name__)


# Taken from rhmsg
class TimeoutHandler(MessagingHandler):
    def __init__(self, url, conf, msgs, *args, **kws):
        super(TimeoutHandler, self).__init__(*args, **kws)
        self.url = url
        self.conf = conf
        self.msgs = msgs
        self.pending = {}

    def on_start(self, event):
        log.debug('Container starting')
        event.container.connected = False
        event.container.error_msgs = []
        if 'cert' in self.conf and 'key' in self.conf and 'cacert' in self.conf:
            ssl = SSLDomain(SSLDomain.MODE_CLIENT)
            ssl.set_credentials(self.conf['cert'], self.conf['key'], None)
            ssl.set_trusted_ca_db(self.conf['cacert'])
            ssl.set_peer_authentication(SSLDomain.VERIFY_PEER)
        else:
            ssl = None
        log.debug('connecting to %s', self.url)
        event.container.connect(url=self.url, reconnect=False, ssl_domain=ssl)
        connect_timeout = self.conf['connect_timeout']
        self.connect_task = event.container.schedule(connect_timeout, self)
        send_timeout = self.conf['send_timeout']
        self.timeout_task = event.container.schedule(send_timeout, self)

    def on_timer_task(self, event):
        if not event.container.connected:
            log.error('not connected, stopping container')
            if self.timeout_task:
                self.timeout_task.cancel()
                self.timeout_task = None
            event.container.stop()
        else:
            # This should only run when called from the timeout task
            log.error('send timeout expired with %s messages unsent, stopping container',
                           len(self.msgs))
            event.container.stop()

    def on_connection_opened(self, event):
        event.container.connected = True
        self.connect_task.cancel()
        self.connect_task = None
        log.debug('connection to %s opened successfully', event.connection.hostname)
        self.send_msgs(event)

    def on_connection_closed(self, event):
        log.debug('disconnected from %s', event.connection.hostname)

    def send_msgs(self, event):
        sender = event.container.create_sender(event.connection, target=self.conf['address'])
        for msg in self.msgs:
            delivery = sender.send(msg)
            log.debug('sent msg: %s', msg.properties)
            self.pending[delivery] = msg
        sender.close()

    def update_pending(self, event):
        msg = self.pending[event.delivery]
        del self.pending[event.delivery]
        log.debug('removed message from self.pending: %s', msg.properties)
        if not self.pending:
            if self.msgs:
                log.error('%s messages unsent (rejected or released)', len(self.msgs))
            else:
                log.debug('all messages sent successfully')
            if self.timeout_task:
                log.debug('canceling timeout task')
                self.timeout_task.cancel()
                self.timeout_task = None
            log.debug('closing connection to %s', event.connection.hostname)
            event.connection.close()

    def on_settled(self, event):
        msg = self.pending[event.delivery]
        self.msgs.remove(msg)
        log.debug('removed message from self.msgs: %s', msg.properties)
        self.update_pending(event)

    def on_rejected(self, event):
        msg = self.pending[event.delivery]
        log.error('message was rejected: %s', msg.properties)
        self.update_pending(event)

    def on_released(self, event):
        msg = self.pending[event.delivery]
        log.error('message was released: %s', msg.properties)
        self.update_pending(event)

    def on_transport_tail_closed(self, event):
        if self.connect_task:
            log.debug('canceling connect timer')
            self.connect_task.cancel()
            self.connect_task = None
        if self.timeout_task:
            log.debug('canceling send timer')
            self.timeout_task.cancel()
            self.timeout_task = None

    def handle_error(self, objtype, event, level=logging.ERROR):
        endpoint = getattr(event, objtype, None)
        condition = (getattr(endpoint, 'remote_condition', None)
                     or getattr(endpoint, 'condition', None))
        if condition:
            name = condition.name
            desc = condition.description
            log.log(level, '%s error: %s: %s', objtype, name, desc)
        else:
            name = '{0} error'.format(objtype)
            desc = 'unspecified'
            log.log(level, 'unspecified %s error', objtype)
        event.container.error_msgs.append((self.url, name, desc))

    def on_connection_error(self, event):
        self.handle_error('connection', event)

    def on_session_error(self, event):
        self.handle_error('session', event)

    def on_link_error(self, event):
        self.handle_error('link', event)
        log.error('closing connection to: %s', event.connection.hostname)
        event.connection.close()

    def on_transport_error(self, event):
        """
        Implement this handler with the same logic as the default handler in
        MessagingHandler, but log to our logger at INFO level, instead of the
        root logger with WARNING level.
        """
        self.handle_error('transport', event, level=logging.INFO)
        if (event.transport
                and event.transport.condition
                and event.transport.condition.name in self.fatal_conditions):
            log.error('closing connection to: %s', event.connection.hostname)
            event.connection.close()


class AMQProducer(object):

    def __init__(self, host=None, port=None,
                 urls=None,
                 certificate=None, private_key=None,
                 trusted_certificates=None,
                 topic=None,
                 timeout=60):
        if isinstance(urls, (list, tuple)):
            pass
        elif urls:
            urls = [urls]
        elif host:
            urls = ['amqps://{0}:{1}'.format(host, port or 5671)]
        else:
            raise RuntimeError('either host or urls must be specified')
        self.urls = urls
        self.conf = {
            'cert': certificate,
            'key': private_key,
            'cacert': trusted_certificates,
            'connect_timeout': timeout,
            'send_timeout': timeout
        }
        if topic:
            self.through_topic(topic)
        else:
            self.address = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def through_topic(self, address):
        self.address = self.build_address('topic', address)

    @staticmethod
    def build_address(channel, address):
        return '{0}://{1}'.format(channel, address)

    def _send_all(self, messages):
        messages = list(messages)
        errors = []
        for url in sorted(self.urls, key=lambda k: random.random()):
            container = Container(TimeoutHandler(url, self.conf, messages))
            container.run()
            errors.extend(container.error_msgs)
            if not messages:
                break
        else:
            error_strs = ['{0}: {1}: {2}'.format(*e) for e in errors]
            raise RuntimeError('could not send {0} message{1} to any destinations, '
                               'errors:\n{2}'.format(len(messages),
                                                     's' if len(messages) != 1 else '',
                                                     '\n'.join(error_strs)))

    def send(self, *messages):
        """
        Send a list of messages.

        Each argument is a proton.Message.
        """
        assert self.address, 'Must call through_queue or through_topic in advance.'

        self.conf['address'] = self.address
        self._send_all(messages)

    def _build_msg(self, props, body, attrs=None):
        """
        Build and return a proton.Message.

        Arguments:
        props (dict): Message properties
        body (object): Message body
        attrs (dict): Attributes to set on the message.
        """
        msg = Message(properties=props, body=body)
        if attrs:
            for name, value in attrs.items():
                setattr(msg, name, value)
        return msg

    def send_msg(self, props, body, **kws):
        """
        Send a single message.

        Arguments:
        props (dict): Message properties
        body (str): Message body. Should be utf-8 encoded text.

        Any keyword arguments will be treated as attributes to set on the
        underlying Message.
        """
        msg = self._build_msg(props, body, kws)
        self.send(msg)

    def send_msgs(self, messages):
        """
        Send a list of messages.

        Arguments:
        messages (list): A list of 2-element lists/tuples.
          tuple[0]: A dict of message headers.
          tuple[1]: Message body. Should be utf-8 encoded text.

        If the tuple has a third element, it is treated as a dict containing
        attributes to be set on the underlying Message.
        """
        msgs = []
        for message in messages:
            msgs.append(self._build_msg(*message))
        self.send(*msgs)


class BeakerMessenger(object):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = BeakerMessenger.__BeakerMessenger()
        return cls.__instance

    class __BeakerMessenger:
        def __init__(self):
            url = get('amq.url')
            cert = get('amq.cert')
            key = get('amq.key')
            cacerts = get('amq.cacerts')
            topic = get('amq.topic_prefix')
            self.producer = AMQProducer(urls=url,
                                        certificate=cert,
                                        private_key=key,
                                        trusted_certificates=cacerts,
                                        topic=topic)

        def send(self, header, body):
            try:
                self.producer.send_msg(header, body)
            except RuntimeError as e:
                log.exception(e)


def _messenger_enabled():
    if _messenger_enabled.res is False:
        _messenger_enabled.res = bool(
            has_proton
            and get('amq.url')
            and get('amq.cert')
            and get('amq.key')
            and get('amq.cacerts')
        )
    return _messenger_enabled.res


_messenger_enabled.res = False


def send_scheduler_update(obj):
    if not _messenger_enabled():
        return

    data = obj.minimal_json_content()
    _send_payload(obj.task_info(), data)


def _send_payload(header, body):
    bkr_msg = BeakerMessenger()
    bkr_msg.send(header, json.dumps(body, default=str))  # pylint: disable=no-member
