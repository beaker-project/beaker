from bkr.server.bexceptions import BeakerException
from bkr.server.recipetasks import RecipeTasks
import bkr.server.model as bkr_model
from bkr.server.model import TaskBase, LabController
from turbogears import config as tg_config
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.common.message_bus import BeakerBus
from bkr.common.helpers import BkrThreadPool
from time import sleep
from threading import Thread
import Queue
import logging
log = logging.getLogger(__name__)

try:
    from qpid.messaging.exceptions import NotFound
    from qpid.messaging import *
    from qpid import datatypes
except ImportError, e:
    pass


class ServerBeakerBus(BeakerBus):

    _queue_timeout = 5
    send_error_suffix = 'Cannot send message'
    rpcroot = RPCRoot()
    _shared_state = {}

    @classmethod
    def do_krb_auth(cls):
        from bkr.common.krb_auth import AuthManager
        principal = tg_config.get('identity.krb_auth_qpid_principal')
        keytab = tg_config.get('identity.krb_auth_qpid_keytab')
        cls._auth_mgr = AuthManager(primary_principal=principal, keytab=keytab)

    def __init__(self, *args, **kw):
        if not self._shared_state:
            state = dict(topic_exchange=tg_config.get('beaker.qpid_topic_exchange'),
                direct_exchange=tg_config.get('beaker.qpid_direct_exchange'),
                service_queue_name=tg_config.get('beaker.qpid_service_queue'),
                _broker=tg_config.get('beaker.qpid_broker'),
                krb_auth=tg_config.get('beaker.qpid_krb_auth'),
                action_threads=[],
                stopped = True,
                thread_handlers={'beaker':
                    {'service_queue': self._service_request_listener,
                    'expired_watchdogs': self._expired_watchdogs_listener,},})
            self._shared_state.update(state)
        self.__dict__.update(self._shared_state)
        super(ServerBeakerBus, self).__init__(*args, **kw)

    def stop(self):
        log.debug('%s is stopping' % self.__class__.__name__)
        self.stopped = True
        self.cleanup()

    def cleanup(self):
        log.debug('%s is cleaning up' % self.__class__.__name__)
        for t in self.action_threads:
            t.join(120)
            if t.isAlive():
                log.warn('Thread %s did not shutdown cleanly' % t.ident)
        BkrThreadPool.join('service-queue', 10)
        self.conn.close()
        log.debug('%s has cleaned up' % self.__class__.__name__)

    def watchdog_notify_sender(self, session, status, watchdog, lc_fqdn, **kw):
            """Notify of watchdog change

            Will send a msg notifying of either a newly activated or newly expired watchdog

            """
            msg_kw = {}
            msg_kw['content'] = {'watchdog' : watchdog, 'status' : status }
            msg_kw['subject'] = 'beaker.Watchdog.%s' % lc_fqdn
            msg = Message(**msg_kw)
            return self.send(session, self.topic_exchange, msg)

    def task_update_sender(self, session, *args, **kw):
            """
            Send msg on Bus with subject 'beaker.TaskUpdate.Jx.RSx.Rx.Tx' only as far as the current task.
            i.e if we're updating a Recipe the subject will not include any tasks
            """
            try:
                task_id = kw.get('id',None)
                if task_id is None:
                    raise BeakerException(_('No valid id passed to task_update: %s' % self.send_error_suffix ))
                #Create full task structure for task i.e J:1.RS:3.R:5
                #FIXME need to create Job/RecipeSet/Recipe object from string here
                sub_subject = ".".join(TaskBase.get_by_t_id(task_id).build_ancestors() + (task_id,))
                msg_kw = {}
                msg_kw['subject'] = 'beaker.TaskUpdate.%s' % sub_subject #FIXME append task_id, get if from the args/kw
                content = kw #FIXME perhaps we don't need all the elements of the dict?
                msg_kw['content'] = content
                msg = Message(**msg_kw)
                self.send(session, self.topic_exchange, msg)
            except BeakerException, e:
                raise BeakerException("%s, %s" % (str(e), self.send_error_suffix))
            except Exception, e:
                raise Exception(("%s, %s" % (str(e), self.send_error_suffix)))

    def _service_queue_worker_logic(self, msg):
        method = msg.properties['method']
        method_args = msg.properties['args']
        msg_kw = {}
        try:
            val_to_return = self.rpcroot.process_rpc(method,method_args)
            msg_kw['content'] = val_to_return
        except Exception, e:
            log.error(str(e))
            msg_kw.setdefault('properties',{'error' : 1 })
            msg_kw['content'] = str(e)
        return msg_kw

    def _service_queue_worker(self):
            tp = BkrThreadPool.get('service-queue')
            while True:
                try:
                    if self.stopped and tp.in_queue.empty():
                        log.debug('Shutting down, cleaned up in_queue service requests')
                        break
                    try:
                        msg = tp.in_queue.get(timeout=self._queue_timeout)
                    except Queue.Empty:
                        pass
                    else:
                        msg_kw = self._service_queue_worker_logic(msg)
                        return_msg  = Message(**msg_kw)
                        return_msg.subject = msg.reply_to
                        if msg.properties.get('qpid.LVQ_key'):
                            return_msg.properties['qpid.LVQ_key'] = msg.properties['qpid.LVQ_key']
                        tp.out_queue.put(return_msg)
                        log.debug('Put response onto service_queue_out')
                except Exception, e:
                    log.exception(str(e))
                    continue

    def _get_receiver_address(self):
        queue_name= self.service_queue_name
        addr_string = queue_name + '; { create: receiver,  \
            node: { type: queue, durable: True, \
            x-declare: { auto-delete: False, exclusive: True, \
            arguments: { \'qpid.policy_type\': ring,  \
            \'qpid.max_size\': 50000000 } }, \
            x-bindings: [ { exchange: "' + self.direct_exchange + '",\
            queue: "' + queue_name + '", } ] } }'
        return addr_string


    def _service_request_listener(self, ssn, *args, **kw):
        try:
            #Start main workers
            BkrThreadPool.create_and_run('service-queue',
                                         target_f=self._service_queue_worker,
                                         target_args=[],
                                         num=10)
            #Start single response worker
            send_response_t = Thread(target=self._send_service_response, args=(ssn,))
            send_response_t.daemon = True
            send_response_t.start()
        except Exception:
            log.exception('service request listener cannot start')
            raise

        #Start single receiver
        self._fetch_service_request(ssn, *args, **kw)

    def _send_service_response(self, ssn):
            tp = BkrThreadPool.get('service-queue')
            while True:
                try:
                    log.debug('Waiting to get from service_queue_out')
                    if self.stopped and tp.out_queue.empty():
                        log.debug('Shutting down, cleaned up out_queue')
                        break
                    try:
                        msg = tp.out_queue.get(timeout=self._queue_timeout)
                    except Queue.Empty:
                        pass
                    else:
                        log.debug('Got from service_queue_out')
                        self.send(ssn, self.direct_exchange, msg)
                except Exception, e:
                    log.exception(str(e))
                    continue

    def _fetch_service_request(self, ssn, *args, **kw):
            #Make sure this thread pool has been created first
            receiver_addr = self._get_receiver_address()
            tp = BkrThreadPool.get('service-queue')
            while True:
                try:
                    if self.stopped:
                        log.debug('Shutting down, '
                            'not receiving any more requests')
                        break
                    msg = self.fetch(ssn,
                                     receiver_addr,
                                     timeout=self._fetch_timeout)
                    if msg is None: # Due to timeout
                        continue
                    tp.in_queue.put(msg)
                    ssn[0].acknowledge()
                except Exception, e:
                    log.exception(str(e))
                    continue

    def _expired_watchdogs_listener(self, ssn):
        rt = RecipeTasks()
        log.debug('Called _expired_watchdogs')
        while True:
            try:
                for lc_id, lc_fqdn in bkr_model.LabController.get_all():
                    watchdog = rt.watchdogs(lc=lc_fqdn, status='expired')
                    if watchdog:
                        log.info('Sending watchdog %s for lc %s' % (watchdog, lc_fqdn))
                        self.watchdog_notify_sender(ssn, 'expired', watchdog, lc_fqdn)
                sleep(60)
                if self.stopped:
                    log.debug('Shutting down, '
                        'sending no more watchdog notifications')
                    break
            except Exception, e:
                log.exception(str(e))
                continue

    def run(self, *args, **kw):
        if not self.stopped:
            log.warn('%s is already running' % self.__class__.__name__)
            return
        self.stopped = False
        listen_to = tg_config.get('beaker.qpid_listen_to', [])
        thread_handlers = self.thread_handlers
        log.debug('Going to Listen to %s' % listen_to)
        for service_msgtype in listen_to:
            try:
                service,type = service_msgtype.split(".")
            except ValueError:
                log.exception(_(u'%s is invalid. Bus services needs to have the format \
                    <system>.<service>' % service_msgtype))
                continue

            try:
                action_pointer = thread_handlers[service][type]
            except KeyError, e:
                log.exception(_(u'No action handler specified for %s'
                % service_msgtype))
                continue

            new_session = self.conn.session()
            log.info('Running %s as thread' % action_pointer)
            new_session = [new_session]
            action_t = Thread(target=action_pointer, args=(new_session,))
            self.action_threads.append(action_t)
            action_t.daemon = True
            action_t.start()
