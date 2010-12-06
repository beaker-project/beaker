# -*- coding: utf-8 -*-
import sys
import time


__all__ = (
    "TaskWatcher",
    "TaskWatcherBus",
    "watch_tasks",
)

_default_listen_depth = None


def display_tasklist_status(task_list):
    state_dict = {}
    for task in task_list:
        for state, value in task.get_state_dict().iteritems():
            state_dict.setdefault(state, 0)
            state_dict[state] += value
    print "--> " + " ".join(( "%s: %s" % (key, state_dict[key]) for key in sorted(state_dict) )) + " [total: %s]" % sum(state_dict.values())


def watch_tasks(hub, task_id_list, indentation_level=0, sleep_time=30, task_url=None):
    """Watch the task statuses until they finish."""
    if not task_id_list:
        return

    try:
        print "Watching tasks (this may be safely interrupted)..."
        task_list = []
        for task_id in sorted(task_id_list):
            task_list.append(TaskWatcher(hub, task_id, indentation_level))

            # print task url if task_url is set or TASK_URL exists in config file
            task_url = task_url or hub._conf.get("TASK_URL", None)
            if task_url is not None:
                print "Task url: %s" % (task_url % task_id)

        while True:
            all_done = True
            changed = False
            for task in task_list:
                changed |= task.update()
                all_done &= task.is_finished()
            if changed:
                display_tasklist_status(task_list)
            if all_done:
                break
            time.sleep(sleep_time)
        return True

    except KeyboardInterrupt:
        running_task_list = [ t.task_id for t in task_list if not t.is_finished() ]
        if running_task_list:
            print "Tasks still running: %s" % running_task_list


class TaskWatcher(object):
    __slots__ = (
        "hub",
        "task_id",
        "task_info",
        "indentation_level",
        "subtask_dict",
        "__dict__",
    )


    display_tasklist_status = staticmethod(display_tasklist_status)
    watch_tasks = staticmethod(watch_tasks)


    def __init__(self, hub, task_id, indentation_level=0):
        self.hub = hub
        self.task_id = task_id
        self.task_info = None
        self.indentation_level = int(indentation_level)
        self.subtask_dict = {}

    def __str__(self):
        result = "%s%s" % ("  " * self.indentation_level, self.task_id)
        if self.task_info:
            result += " %s" % self.task_info["method"]
        return result

    def is_finished(self):
        """Is the task finished?"""
        if self.task_info is None:
            return False

        result = self.task_info.get("is_finished", False)
        for subtask in self.subtask_dict.itervalues():
            result &= subtask.is_finished()
        return result


    def is_failed(self):
        """Did the task fail?"""
        if self.task_info is None:
            return False
        return self.task_info.get("is_failed", False)


    def display_state(self, task_info):
        worker = task_info.get("worker")
        if worker is not None:
            return "%s (%s)" % (task_info["state_label"], worker["name"])
        return "%s" % task_info["state_label"]


    def update(self):
        """Update info and log if needed. Returns True on state change."""
        if self.is_finished():
            return False

        last = self.task_info
        self.task_info = self.hub.taskactions.task_info(self.task_id, False)

        if self.task_info is None:
            print "No such task id: %s" % self.task_id
            sys.exit(1)

        # watch new tasks
        for i in self.task_info.get("subtask_id_list", []):
            if i not in self.subtask_dict:
                self.subtask_dict[i] = TaskWatcher(self.hub, i, self.indentation_level + 1)

        changed = False
        state = self.task_info["state"]
        if last:
            # compare and note status changes
            laststate = last["state"]
            if laststate != state:
                print "%s: %s -> %s" % (self, self.display_state(last), self.display_state(self.task_info))
                changed = True
        else:
            # first time we're seeing this task, so just show the current state
            print "%s: %s" % (self, self.display_state(self.task_info))
            changed = True

        # update all subtasks
        for key in sorted(self.subtask_dict.keys()):
            changed |= self.subtask_dict[key].update()
        return changed


    def get_state_dict(self):
        state_dict = {}
        if self.task_info is not None:
            state = self.task_info.get("state_label", "unknown")
            state_dict.setdefault(state, 0)
            state_dict[state] += 1

        for subtask in self.subtask_dict.itervalues():
            for state, value in subtask.get_state_dict().iteritems():
                state_dict.setdefault(state, 0)
                state_dict[state] += value

        return state_dict

class TaskWatcherBus(TaskWatcher):

    listening_root_tasks = []
    listen_depth = _default_listen_depth
    task_list = []
    task_depth_order = ['J','RS','R','T']

    def __init__(self, task_id, *args, **kw):
        super(TaskWatcherBus,self).__init__(None, task_id, *args, **kw)
        #FIXME Do I really need to be access dict explicitly?
        self.__dict__['hub'] = None #ensure hub is None
        self.__dict__['is_failed'] = None
        self.__dict__['update'] = None
        self.__dict__['root_elem'] =  task_id

    @classmethod
    def get_by_id(cls,id):
        for task_instance in cls.task_list:
            if id == task_instance.task_id:
                return task_instance
        raise ValueError(u'No task found with id %s' % id)

    @classmethod
    def _get_type(cls,task_id):
        type,id = task_id.split(':')
        return type

    @classmethod
    def _get_depth(cls,ancestor,desc):
        from math import fabs
        return int(fabs(cls.task_depth_order.index(desc) -
            cls.task_depth_order.index(ancestor)))

    @classmethod
    def add_watch_task_from_wire(cls, task_id, ancestor_list):
        """
        This method is for adding a newly unseen task and gettings its indenting right
        It tries to determine how many levels up it's ancestor (that was specified at the shell)
        and adjust it's indentation level accordingly
        """
        lrt = cls.listening_root_tasks
        for ancestor in ancestor_list:
            if ancestor in lrt:
                ancestor_task = cls.get_by_id(ancestor)
                depth_level = cls.task_depth_order.index(cls._get_type(task_id)) -\
                    cls.task_depth_order.index(cls._get_type(ancestor)) #Get the depth difference between them
                new_task = TaskWatcherBus(task_id, indentation_level=ancestor_task.indentation_level + depth_level)
                cls._append_new_task(new_task)
                return new_task
        raise ValueError(u'Cannot find valid ancestor for %s in %s' % (task.task_id, ancestor_list))


    @classmethod
    def _append_new_task(cls,task):
        cls.task_list.append(task)

    @classmethod
    def watch_tasks(cls, listenuntil, task_id_list, indentation_level=0, *args):
        try:
            from bkr.client.message_bus import ClientBeakerBus
            bb = ClientBeakerBus()
            watching_task = cls._get_type(task_id_list[:1].pop())
            if listenuntil is None:
                listenuntil = watching_task
            # 0 becomes current_level depth (i.e 0 + 1)
            cls.listen_depth = cls._get_depth(watching_task, listenuntil) + 1
            print 'Watching tasks via bus (this may be safely interrupted)...'
            for task_id in sorted(task_id_list):
                try:
                    current_task_info = bb.send_action('service_queue', 'taskactions.task_info', task_id) #Seperate call for each id
                except Exception, e:
                    print 'Could not succesfully recieve msg from bus'
                    return
                task = cls(task_id)
                task._add_print_task_info(current_task_info)
                cls._append_new_task(task)
                cls.listening_root_tasks.append(task_id)

            cls.display_tasklist_status(cls.task_list)
            finished = False
            for t in cls.task_list:
                finished = t.is_finished()
            if cls.task_list and finished is False:
                bb.run(task_id_list)
        except KeyboardInterrupt:
            if cls.listening_root_tasks:
                print 'Tasks still running %s' % cls.listening_root_tasks

    def is_finished(self):
        """Returns True is no more tasks are left to run

        is_finished() returns true when it determines there are no more events to listen for
        It does this by ascertaining whether all of the task_ids passed in have already finished

        """
        lrt = self.listening_root_tasks
        if self.task_id in lrt:
            finished =  self.task_info['is_finished']
            if finished:
                lrt.remove(self.task_id)
            if not lrt: #nothing left to listen for
                return True
            return False

        return False

    def _add_print_task_info(self,new_task_info=None):
        if self.task_info is not None:
            self.print_state_change(new_task_info)
            self.task_info = new_task_info
        else:
            self.task_info = new_task_info
            self.print_state()


    def print_state(self):
        print "%s: %s" % (self, self.display_state(self.task_info))

    def print_state_change(self,latest):
        print "%s: %s -> %s" % (self, self.display_state(self.task_info), self.display_state(latest))

    def error(self,error_content):
        print error_content #print error message and not much more

    def process_change(self, task_info):
        self._add_print_task_info(task_info)
        self.display_tasklist_status(self.task_list)
        return self.is_finished()
