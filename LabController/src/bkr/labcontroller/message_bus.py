
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

try:
    from qpid.messaging import *
    from qpid.log import enable, ERROR
    from qpid import datatypes
except ImportError:
    pass


from threading import Thread
from xmlrpclib import Fault as xmlrpclibFault

import ConfigParser, os, socket
from time import sleep
from bkr.common.message_bus import BeakerBus
from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.config import get_conf

import logging
log = logging.getLogger(__name__)
conf = get_conf()

class LabBeakerBus(BeakerBus):

    lc = socket.gethostname()
    global conf
    __conf = conf
    topic_exchange = __conf.get('QPID_TOPIC_EXCHANGE')
    direct_exchange = __conf.get('QPID_DIRECT_EXCHANGE')
    service_queue_name = __conf.get('QPID_SERVICE_QUEUE')
    _broker = __conf.get('QPID_BROKER')
    krb_auth = __conf.get('QPID_KRB_AUTH')
    stopped = True
    _shared_state = {}


    @classmethod
    def do_krb_auth(cls):
        from bkr.common.krb_auth import AuthManager
        principal = cls.__conf.get('QPID_KRB_PRINCIPAL')
        keytab = cls.__conf.get('QPID_KRB_KEYTAB')
        cls._auth_mgr = AuthManager(primary_principal=principal, keytab=keytab)

    def __init__(self, watchdog=None, *args, **kw):
        super(LabBeakerBus,self).__init__(*args, **kw)
        if not self._shared_state:
            self._shared_state = dict(thread_handlers=
                {'beaker': {'watchdog':  self._watchdog_listener,}},
                threads=[],
                watchdog=watchdog)
        self.__dict__.update(self._shared_state)

    def stop(self):
        self.stopped = True

    def run(self, services, *args, **kw):
        if not self.stopped:
            log.warn('%s is already running' % self.__class__.__name__)
            return
        self.stopped = False
        for service in services:
            system, service_name = service.split('.')
            system_key = self.thread_handlers[system]
            service = system_key.get(service_name)
            session = [self.conn.session()]
            thread = Thread(target=service, args=(session,) + args, kwargs=kw)
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

        while True:
            # This is a poor attempt to slow down any attempt to fill up our logs
            # by creating bad messages
            sleep(2)
            try:
                if self.stopped:
                    log.info('Shutting down,'
                        'no longer receiving watchdog notifications')
                    break
                log.debug('Waiting in watchdog')
                message = self.fetch(session, addr_string, timeout=self._fetch_timeout)
                if message is None:
                    continue
                log.debug('Got message %s' % message)
                try:
                    watchdog_data = message.content['watchdog']
                except KeyError:
                    log.exception(u"msg content has no key 'watchdog'")
                    session[0].acknowledge()
                    continue
                try:
                    status = message.content['status']
                except KeyError:
                    log.exception(u"msg content has no key 'status'")
                    session[0].acknowledge()
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
                    session[0].acknowledge()
                except xmlrpclibFault, e:
                    # We should probably retry this one
                    log.exception(str(e))
            except Exception, e:
                # It could just be bad message data
                # Let's log it then acknowledge it to make sure we don't get
                # the same message
                log.exception(str(e))
                session[0].acknowledge()
