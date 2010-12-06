from qpid.messaging import *
from qpid.log import enable, DEBUG, WARN, ERROR
from qpid import datatypes
from bkr.client.task_watcher import TaskWatcherBus
enable("qpid.messaging", ERROR)
from bkr.common.message_bus import BeakerBus

class ClientBeakerBus(BeakerBus):


    def __init__(self, hub=None, *args, **kw):
        super(ClientBeakerBus,self).__init__(*args, **kw)

    def run(self, task_ids):
        # TODO add listen config section like bkr-server
        session = self.conn.session()
        self.ListenHandlers().task_watch(session, task_ids)

    class SendHandlers(BeakerBus.SendHandlers):
        pass


    class ListenHandlers(BeakerBus.ListenHandlers):


        def task_watch(self, session, t_id_list, *args, **kw):
            def _deal_with(content):
                if content['is_finished']:
                    return False

            listen_depth = TaskWatcherBus.listen_depth
            depth_string = ''
            for loop in range(listen_depth):
                for t_id in t_id_list:
                    queue_name = 'tmp.beaker-events-client' + str(datatypes.uuid4())
                    addr_string = queue_name + '; { create: receiver,  \
                            node: { type: queue, durable: False,  \
                        x-declare: { exclusive: True, auto-delete: True },  \
                        x-bindings: [ {  exchange: "' + ClientBeakerBus.topic_exchange + '", queue: "' + queue_name + '", \
                                        key: "TaskUpdate.#.' + t_id + depth_string+'" } ] } }'
                    new_receiver = session.receiver(addr_string)
                    new_receiver.capacity = 10
                depth_string += '.*'
            try:
                #First get current status
                while True:
                    message = session.next_receiver().fetch()
                    error = message.properties.get('error')
                    content = message.content
                    session.acknowledge()
                    t_id = content['id']
                    try:
                        task = TaskWatcherBus.get_by_id(t_id)
                    except ValueError, e: #Perhaps we got a sub task 
                        subject_with_ancestors = message.subject
                        #Trim the fat from our subject and reverse to get ancestors
                        #So it goes from 'TaskUpdate.J:1.RS:2.R:3' to [RS:2,J:1]
                        ancestors = subject_with_ancestors.split('.')[1:-1]
                        ancestors.reverse()
                        task = TaskWatcherBus.add_watch_task_from_wire(t_id,ancestors)
                    if error:
                        task.error(content)
                        break
                    is_finished = task.process_change(content)
                    if is_finished:
                        break
            except KeyboardInterrupt:
                pass

