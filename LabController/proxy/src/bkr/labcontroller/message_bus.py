import logging
import kobo.conf
from threading import Thread
from qpid.messaging import *
from qpid.log import enable, DEBUG, WARN, ERROR
from bkr.log import add_stderr_logger, add_rotating_file_logger
from qpid import datatypes

import ConfigParser, os
from bkr.common.message_bus import BeakerBus
from bkr.labcontroller.proxy import Watchdog

VERBOSE_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] {%(process)5d} %(name)s.%(module)s:%(lineno)4d %(message)s"
log = logging.getLogger("Bus")
log.setLevel(logging.DEBUG)
config = kobo.conf.PyConfigParser()
# load default config
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
config.load_from_file(default_config)
log_level = logging._levelNames.get(config["LOG_LEVEL"].upper())
log_file = config["MSG_BUS_LOG_FILE"]
#enable("qpid.messaging", ERROR, log_file) FIXME I think this will cause problems if I enable it to the same file
add_rotating_file_logger(log,
    log_file, log_level=log_level, format=VERBOSE_LOG_FORMAT)

class LabBeakerBus(BeakerBus):

    _running = {}
    def __init__(self, lc=None, *args, **kw):
        super(LabBeakerBus,self).__init__(*args, **kw)
        self.lc = lc
        self.thread_handlers.update({'beaker' : { 'watchdog' :  self.ListenHandlers._watchdog }})
        self.threads = []

    def run(self, service=None, *args, **kw):
        if service:
            try:
                system, service_name = service.split('.')
            except ValueError:
                err_msg = 'Bus services needs to have the format <system>.<service>'
                log.error(err_msg)
                raise(err_msg)
            if not self._is_running(system, service_name):
                try:
                    system_key = self.thread_handlers.get(system)
                    if system_key:
                        service = system_key.get(service_name)
                        if service:
                            thread = Thread(target=service, args=(self.conn.session(),) + args, kwargs=kw)
                            thread.setDaemon(False)
                            thread.start()
                            self.threads.append(thread)
                except TypeError:
                    err_msg = '%s is not a valid service' % service
                    log.error(err_msg)
                    raise
                self._mark_running(system, service_name)
                for t in self.threads:
                    t.join()
        else: #run them all
            for system, services in self.thread_handlers.iteritems():
                for service_name, service in services:
                    args = []
                    if not self._is_running(system, service_name):
                        if system == 'beaker' and service_name == 'watchdog':
                            args = [self.lc]
                        service(self.conn.session(),*args)
                        self._mark_running(system, service_name)

    @classmethod
    def _is_running(cls, system, service_name):
        if not cls._running.get(system):
            return False
        elif cls._running.get(system).count(service_name):
            return True
        else:
            return False

    @classmethod
    def _mark_running(cls, system, service_name):
        if cls._running.get(system):
            cls._running[system].append(service_name)
        else:
            cls._running[system] = [service_name]


    class SendHandlers(BeakerBus.SendHandlers):
        pass


    class ListenHandlers(BeakerBus.ListenHandlers):
 
        @classmethod
        def _watchdog(cls, session, lc, *args, **kw):
            print 'Session %s' % session

            if not lc:
                raise Exception('Watchdog needs to listen to a LabController, none specified')
            lc = 'lab.rhts.englab.bne.redhat.com:9010'
            queue_name = 'lab-watchdog-%s' % lc
            log.debug('_watchdog listening for lc %s' % lc)
            addr_string = queue_name + '; { create: always,  \
                    node: { type: queue, durable: True,  \
                    x-declare: { exclusive: True, auto-delete: False }}}'
                    #x-bindings: [ {  queue: "' + queue_name + '"} ] }}'

            log.info('Listening with addr %s' % addr_string )
            # FIXME exception handling
            # Also, if dies, need to remove from 'running'
            watchdog = Watchdog(conf=config, logger=log)
            receiver = session.receiver(addr_string)
            while True:
                log.debug('Waiting in _watchdog')
                message = receiver.fetch()
                try:
                    log.debug('Got message %s' % message)
                    watchdog_data = message.content['watchdog']
                    status = message.content['status']
                    if 'active' == status:
                        log.debug('Calling active_watchdogs %s' %  watchdog_data)
                        watchdog.active_watchdogs(watchdog_data)
                    elif 'expired' == status:
                        log.debug('Calling expired_watchdogs %s' %  watchdog_data)
                        watchdog.expire_watchdogs(watchdog_data)
                except Exception, e:
                    log.exception(str(e))
                    # Something wrong with the packet we are receiving,
                    # We don't want to be continually spammed with it
                    session.acknowledge()
                #FIXME seperate out methods in proxy.py and call from here
