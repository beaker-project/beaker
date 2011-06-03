from qpid.messaging import *
from qpid import datatypes
from qpid.util import URL
from qpid.log import enable, DEBUG, WARN
from bkr.server.bexceptions import BeakerException
import bkr.server.model as bkr_model
from bkr.server.model import TaskBase, LabController
from bkr.server.recipetasks import RecipeTasks
from bkr.server import scheduler
from turbogears import config
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.common.message_bus import BeakerBus
from bkr.common.helpers import thread
from time import sleep

import logging
log = logging.getLogger("bkr.server.mrg")

VALID_AMQP_TYPES=[list,dict,bool,int,long,float,unicode,dict,list,str,type(None)]


class ServerBeakerBus(BeakerBus):


    class SendHandlers(object):
        error_suffix = 'Cannot send message'

        @classmethod
        def watchdog_notify(cls, session, status, watchdog, lc_fqdn, **kw):
            """Notify of watchdog change

            Will send a msg notifying of either a newly activated or newly expired watchdog

            """
            try:
                msg_kw = {}
                msg_kw['content'] = {'watchdog' : watchdog, 'status' : status }
                msg = Message(**msg_kw)
                lc_fqdn = 'lab.rhts.englab.bne.redhat.com:9010' #FIXME testing
                snd = session.sender("lab-watchdog-%s" % lc_fqdn)
                snd.send(msg)
                log.info('Sent msg %s' % msg)
            except Exception, e:
                raise Exception(("%s, %s" % (str(e), cls.error_suffix)))
    
        @classmethod
        def task_update(cls,session, *args, **kw):
            """
            Send msg on Bus with subject 'TaskUpdate.Jx.RSx.Rx.Tx' only as far as the current task.
            i.e if we're updating a Recipe the subject will not include any tasks
            """
    
            try:
                task_id = kw.get('id',None)
                if task_id is None:
                    raise BeakerException(_('No valid id passed to task_update: %s' % cls.error_suffix ))
                #Create full task structure for task i.e J:1.RS:3.R:5
                #FIXME need to create Job/RecipeSet/Recipe object from string here
                sub_subject = ".".join(TaskBase.get_by_t_id(task_id).build_ancestors() + (task_id,))
                msg_kw = {}
                msg_kw['subject'] = 'TaskUpdate.%s' % sub_subject #FIXME append task_id, get if from the args/kw
                content = kw #FIXME perhaps we don't need all the elements of the dict?
                msg_kw['content'] = content
                msg = Message(**msg_kw) 
                snd = session.sender(ServerBeakerBus.topic_exchange) 
                snd.send(msg)
                log.info('Sent msg %s' % msg_kw['subject'])
            except BeakerException, e:
                raise BeakerException("%s, %s" % (str(e), cls.error_suffix))
            except Exception, e:
                raise Exception(("%s, %s" % (str(e), cls.error_suffix)))

    class ListenHandlers(object):
        rpc = RPCRoot()
    
        @classmethod
        @thread
        def _koji_task_state_change(cls, ssn, *args, **kw):
            queue_name = 'tmp.koji-events-client-' + str(datatypes.uuid4())
            try:
                receiver = ssn.receiver(queue_name + '; { create: receiver, ' +
                                    '      node: { type: queue, durable: False, ' +
                                    ' x-declare: { exclusive: True, auto-delete: False }, ' +
                                    'x-bindings: [ {  exchange: "koji.events", queue: "' + queue_name + '", ' +
                                    '                 arguments: { x-match: any, type: TaskStateChange } } ] } }')
            except NotFound, e:
                log.error(e)
    
            while True:
                msg = receiver.fetch()
                #FIXME Do something with message
                ssn.acknowledge()

        @classmethod
        @thread
        def _service_request(cls,ssn, *args, **kw):
            queue_name='tmp.beaker-service-queue'
            try:

                receiver = ssn.receiver(queue_name + '; { create: always, ' +
                                    '      node: { type: queue, durable: True, ' +
                                    ' x-declare: { auto-delete: False }, ' +
                                    'x-bindings: [ {  queue: "' + queue_name + '", } ] } }')

                while True:
                    log.debug('Waiting to receive in _service_request')
                    msg = receiver.fetch()
                    method = msg.properties['method']
                    method_args = msg.properties['args']
                    reply_to = msg.reply_to
                    msg_kw = {}
                    try:
                        val_to_return = cls.rpc.process_rpc(method,method_args)
                        msg_kw['content'] = val_to_return
                    except Exception, e:
                        log.error(str(e))
                        msg_kw.setdefault('properties',{'error' : 1 })
                        msg_kw['content'] = str(e)
                    msg = Message(**msg_kw) #FIXME Do I need to add an unique id ??
                    try:
                        snd = ssn.sender(reply_to)
                        log.debug('Sent msg %s' %  msg_kw['content'])
                        snd.send(msg)
                        ssn.acknowledge() #Not sure if this is sync/async
                    except Exception, e:
                        log.error(str(e))
            except NotFound, e:
                log.error(e)

        @classmethod
        @thread
        def _expired_watchdogs(cls, ssn):
            rt = RecipeTasks()
            log.debug('Called _expired_watchdogs')
            while True:
                for lc_id, lc_fqdn in bkr_model.LabController.get_all():
                    watchdog = rt.watchdogs(lc=lc_fqdn, status='expired')
                    if watchdog:
                        log.info('Sending watchdog %s for lc %s' % (watchdog, lc_fqdn))
                        ServerBeakerBus().send_action('watchdog_notify', 'expired', watchdog, lc_fqdn)
                sleep(60)


    def __init__(self, *args, **kw):
        super(ServerBeakerBus, self).__init__(*args, **kw)
        self.thread_handlers.update(
            {'beaker' :
                {'service_queue' : self.ListenHandlers._service_request, 
                 'expired_watchdogs' : self.ListenHandlers._expired_watchdogs,},
            }
        )

    def run(self, *args, **kw):
        listen_to = config.get('beaker.qpid_listen_to', [])
        thread_handlers = self.thread_handlers
        for service_msgtype in listen_to:
            service,type = service_msgtype.split(".")
            try:
                action_pointer = thread_handlers[service][type]
            except KeyError, e:
                log.exception(_('No action handler specified for %s'
                % service_msgtype))
            new_session = self.conn.session()
            action_pointer(new_session)

    def _open_connection(self, *args, **kw):
        try:
            self.conn.open()
        except ConnectionError, e:
            if 'already open' in str(e):
                pass
            else:
                raise


