try:
    from qpid.messaging import *
    from qpid.log import enable, ERROR
    from qpid import datatypes
except ImportError:
    pass


from threading import Thread
from bkr.log import add_stderr_logger
from bkr.labcontroller.utils import add_rotating_file_logger
from xmlrpclib import Fault as xmlrpclibFault

import ConfigParser, os, socket
from time import sleep
from bkr.common.message_bus import BeakerBus
from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.config import get_conf

import logging
log = logging.getLogger(__name__)
conf = get_conf()
log_level_string = conf.get("QPID_BUS_LOG_LEVEL") or conf["LOG_LEVEL"]
log_level = getattr(logging, log_level_string.upper(), logging.DEBUG)
log_file = conf["QPID_BUS_LOG_FILE"]

add_rotating_file_logger(log,
                        log_file,
                        log_level=log_level,
                        format=conf['VERBOSE_LOG_FORMAT'])

class LabBeakerBus(BeakerBus):

    lc = socket.gethostname()
    global conf
    __conf = conf
    topic_exchange = __conf.get('QPID_TOPIC_EXCHANGE')
    direct_exchange = __conf.get('QPID_DIRECT_EXCHANGE')
    service_queue_name = __conf.get('QPID_SERVICE_QUEUE')
    _broker = __conf.get('QPID_BROKER')
    krb_auth = __conf.get('QPID_KRB_AUTH')

    @classmethod
    def do_krb_auth(cls):
        from bkr.common.krb_auth import AuthManager
        principal = cls.__conf.get('QPID_KRB_PRINCIPAL')
        keytab = cls.__conf.get('QPID_KRB_KEYTAB')
        cls._auth_mgr = AuthManager(primary_principal=principal, keytab=keytab)

    def __init__(self, watchdog=None, *args, **kw):
        super(LabBeakerBus,self).__init__(*args, **kw)
        self.thread_handlers.update({'beaker' : { 'watchdog' :  self._watchdog_listener,}})
        self.threads = []

        self.watchdog = watchdog

    def run(self, services, *args, **kw):
        for service in services:
            system, service_name = service.split('.')
            system_key = self.thread_handlers[system]
            service = system_key.get(service_name)
            thread = Thread(target=service, args=(self.conn.session(),) + args, kwargs=kw)
            self.threads.append(thread)
            thread.setDaemon(False)
            thread.start()

    def _watchdog_listener(self, session, *args, **kw):
        lc = self.lc
        if not lc:
            raise Exception('Watchdog needs to listen to a LabController, none specified')

        queue_name = 'tmp.lab-watchdog' + str(datatypes.uuid4())
        log.debug('_watchdog listening for lc %s' % lc)
        addr_string = queue_name + '; { create: receiver,  \
                node: { type: queue, durable: False,  \
                x-declare: { exclusive: True, auto-delete: True, \
                             arguments: { \'qpid.policy_type\': ring, \
                                          \'qpid.max_size\': 50000000 } }, \
                x-bindings :[{ exchange :"' + self.topic_exchange + '", queue: "' + queue_name +'", \
                               key: "beaker.Watchdog.' + lc +'"}]}}'

        receiver = session.receiver(addr_string)

        while True:
            # This is a poor attempt to slow down any attempt to fill up our logs
            # by creating bad messages
            sleep(2)
            try:
                log.debug('Waiting in watchdog')
                message = receiver.fetch()
                log.debug('Got message %s' % message)

                try:
                    watchdog_data = message.content['watchdog']
                except KeyError:
                    log.exception(u"msg content has no key 'watchdog'")
                    session.acknowledge()
                    continue
                try:
                    status = message.content['status']
                except KeyError:
                    log.exception(u"msg content has no key 'status'")
                    session.acknowledge()
                    continue

                try:
                    if 'active' == status:
                        log.debug('Calling active_watchdogs %s' %  watchdog_data)
                        self.watchdog.active_watchdogs(watchdog_data, purge=False)
                    elif 'expired' == status:
                        log.debug('Calling expire_watchdogs %s' %  watchdog_data)
                        self.watchdog.expire_watchdogs(watchdog_data)
                    elif 'removed' == status:
                        data = watchdog_data[0]
                        w_key = '%s:%s' % (data['system'], data['recipe_id'])
                        log.debug('Calling purge_old_watchdog %s' % watchdog_data)
                        self.watchdog.purge_old_watchdog(w_key)
                    else:
                        raise ValueError("status in watchdog message content should be 'expired' \
                            or 'active' ")
                    session.acknowledge()
                except xmlrpclibFault, e:
                    # We should probably retry this one
                    log.exception(str(e))
            except Exception, e:
                # It could just be bad message data
                # Let's log it then acknowledge it to make sure we don't get
                # the same message
                log.exception(str(e))
                session.acknowledge()


