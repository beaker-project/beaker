from bkr.client.task_watcher import TaskWatcherBus

from bkr.common.message_bus import BeakerBus
from bkr.client import conf

try:
    from qpid import datatypes
except ImportError, e:
    pass

class ClientBeakerBus(BeakerBus):

    topic_exchange = conf.get('QPID_TOPIC_EXCHANGE')
    direct_exchange = conf.get('QPID_DIRECT_EXCHANGE')
    service_queue_name = conf.get('QPID_SERVICE_QUEUE')

    _broker = conf.get('QPID_BROKER')

    if conf.get('QPID_KRB') is True:
        krb_auth = True
    else:
        krb_auth = False

    @classmethod
    def do_krb_auth(cls):
        from bkr.common.krb_auth import AuthManager
        principal = conf.get('KRB_PRINCIPAL')
        keytab = conf.get('KRB_KEYTAB')
        # If they do not specify principal and keytab
        # then we will use the default ticket cache automatically
        if principal and keytab:
            cls._auth_mgr = AuthManager(primary_principal=principal, keytab=keytab)

    def __init__(self, hub=None,task_watcher=None, *args, **kw):
        super(ClientBeakerBus,self).__init__(*args, **kw)
        self.task_watcher = task_watcher

    def run(self, task_ids):
        # TODO add listen config section like bkr-server
        session = self.conn.session()
        self.task_watch(session, task_ids)

    def task_watch(self, session, t_id_list, *args, **kw):
        def _deal_with(content):
            if content['is_finished']:
                return False

        listen_depth = self.task_watcher.listen_depth
        depth_string = ''
        for loop in range(listen_depth):
            for t_id in t_id_list:
                queue_name = 'tmp.beaker-events-client' + str(datatypes.uuid4())
                addr_string = queue_name + '; { create: receiver,  \
                        node: { type: queue, durable: False,  \
                    x-declare: { exclusive: True, auto-delete: True, \
                                 arguments: { \'qpid.policy_type\': ring, \
                                              \'qpid.max_size\': 50000000 } },  \
                    x-bindings: [ {  exchange: "' + self.topic_exchange + '", queue: "' + queue_name + '", \
                                    key: "beaker.TaskUpdate.#.' + t_id + depth_string+'" } ] } }'
                new_receiver = session.receiver(addr_string)
                new_receiver.capacity = 10
            depth_string += '.*'
        try:
            while True:
                message = session.next_receiver().fetch()
                error = message.properties.get('error')
                content = message.content
                session.acknowledge()
                t_id = content['id']
                try:
                    task = self.task_watcher.get_by_id(t_id)
                except ValueError, e: #Perhaps we got a sub task
                    subject_with_ancestors = message.subject
                    #Trim the fat from our subject and reverse to get ancestors
                    #So it goes from 'beaker.TaskUpdate.J:1.RS:2.R:3' to [RS:2,J:1]
                    ancestors = subject_with_ancestors.split('.')[2:-1]
                    ancestors.reverse()
                    task = self.task_watcher.add_watch_task_from_wire(t_id,ancestors)
                if error:
                    task.error(content)
                    break
                #Prints task status
                task.process_change(content)
                #Displays task-watcher status, and returns True if finished
                is_finished = self.task_watcher.process_change()
                if is_finished:
                    break
        except KeyboardInterrupt:
            pass

