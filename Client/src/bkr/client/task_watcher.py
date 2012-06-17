# -*- coding: utf-8 -*-
import sys
import time


__all__ = (
    "TaskWatcher",
    "TaskWatcherBus",
    "TaskBus",
    "watch_bus_tasks",
    "watch_tasks"
)

_default_listen_depth = None

def watch_bus_tasks(listenuntil, task_id_list, indentation_level=0, *args):
    try:
        from bkr.client.message_bus import ClientBeakerBus
        watcher = TaskWatcherBus()
        bb = ClientBeakerBus(task_watcher=watcher)
        watching_task = TaskBus.get_type(task_id_list[:1].pop())
        if not listenuntil:
            listenuntil = 0
        # 0 becomes current_level depth (i.e 0 + 1)
        watcher.listen_depth = TaskBus.get_depth(watching_task, listenuntil) + 1
        print 'Watching tasks via bus (this may be safely interrupted)...'
        for task_id in sorted(task_id_list):
            try:
                current_task_info = bb.rpc.taskactions.task_info(task_id) #Seperate call for each id
            except Exception, e:
                print 'Could not succesfully recieve msg from bus:%s' % (str(e))
                return
            task = TaskBus(task_id)
            task.add_print_task_info(current_task_info)
            watcher.append_new_task(task)
            watcher.listening_root_tasks.append(task_id)

        TaskWatcherBus.display_tasklist_status(watcher.task_list)
        finished = watcher.is_finished()

        if watcher.task_list and finished is False:
            bb.run(task_id_list)

        is_failed = watcher.is_failed()
    except KeyboardInterrupt:
        if watcher.listening_root_tasks:
            print 'Tasks still running %s' % watcher.listening_root_tasks
            is_failed = True
    return is_failed

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
        watcher = TaskWatcher()
        for task_id in sorted(task_id_list):
            watcher.task_list.append(Task(hub, task_id, indentation_level))
            # print task url if task_url is set or TASK_URL exists in config file
            task_url = task_url or hub._conf.get("TASK_URL", None)
            if task_url is not None:
                print "Task url: %s" % (task_url % task_id)
        is_failed = False
        while True:
            all_done = True
            changed = False
            for task in watcher.task_list:
                changed |= watcher.update(task)
                is_failed |= watcher.is_failed(task)
                all_done &= watcher.is_finished(task)
            if changed:
                display_tasklist_status(watcher.task_list)
            if all_done:
                break
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        running_task_list = [ t.task_id for t in watcher.task_list if not watcher.is_finished(t) ]
        if running_task_list:
            print "Tasks still running: %s" % running_task_list
            # Don't report pass on jobs still running.
            is_failed = True
    return is_failed

class TaskWatcher(object):

    display_tasklist_status = staticmethod(display_tasklist_status)

    def __init__(self):
        self.subtask_dict = {}
        self.task_list = []

    def is_finished(self, task):
        """Is the task finished?"""
        if task.task_info is None:
            return False

        result = task.task_info.get("is_finished", False)
        for subtask in self.subtask_dict.itervalues():
            result &= subtask.is_finished()
        return result

    def is_failed(self, task):
        """Did the task Fail?"""
        if task.task_info is None:
            return False

        result = task.task_info.get("is_failed", False)
        for subtask in self.subtask_dict.itervalues():
            result |= subtask.is_failed()
        return result

    def update(self, task):
        """Update info and log if needed. Returns True on state change."""
        if self.is_finished(task):
            return False

        last = task.task_info
        task.task_info = task.hub.taskactions.task_info(task.task_id, False)

        if task.task_info is None:
            print "No such task id: %s" % task.task_id
            sys.exit(1)

        # watch new tasks
        for i in task.task_info.get("subtask_id_list", []):
            if i not in self.subtask_dict:
                self.subtask_dict[i] = Task(task.hub, i, self.indentation_level + 1)

        changed = False
        state = task.task_info["state"]
        if last:
            # compare and note status changes
            laststate = last["state"]
            if laststate != state:
                print "%s: %s -> %s" % (task, task.display_state(last), task.display_state(task.task_info))
                changed = True
        else:
            # first time we're seeing this task, so just show the current state
            print "%s: %s" % (task, task.display_state(task.task_info))
            changed = True

        # update all subtasks
        for key in sorted(self.subtask_dict.keys()):
            changed |= self.subtask_dict[key].update()
        return changed


class Task(object):

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


    def __init__(self):
        self.task_list = []
        self.listening_root_tasks = []
        self.listen_depth = _default_listen_depth

    def process_change(self):
        self.display_tasklist_status(self.task_list)
        return self.is_finished()

    def get_by_id(self,id):
        for task_instance in self.task_list:
            if id == task_instance.task_id:
                return task_instance
        raise ValueError(u'No task found with id %s' % id)

    def add_watch_task_from_wire(self, task_id, ancestor_list):
        """
        This method is for adding a newly unseen task and gettings its indenting right
        It tries to determine how many levels up it's ancestor (that was specified at the shell)
        and adjust it's indentation level accordingly
        """
        lrt = self.listening_root_tasks
        for ancestor in ancestor_list:
            if ancestor in lrt:
                ancestor_task = self.get_by_id(ancestor)
                depth_level = TaskBus.task_depth_order.index(TaskBus.get_type(task_id)) -\
                    TaskBus.task_depth_order.index(TaskBus.get_type(ancestor)) #Get the depth difference between them
                new_task = TaskBus(task_id, indentation_level=ancestor_task.indentation_level + depth_level)
                self.append_new_task(new_task)
                return new_task
        raise ValueError(u'Cannot find valid ancestor for %s in %s' % (task.task_id, ancestor_list))

    def append_new_task(self,task):
        self.task_list.append(task)


    def is_finished(self):
        """Returns True is no more tasks are left to run

        is_finished() returns true when it determines there are no more events to listen for
        It does this by ascertaining whether all of the task_ids passed in have already finished

        """
        lrt = self.listening_root_tasks
        for task in self.task_list :
            if task.task_id in lrt:
                finished =  task.task_info['is_finished']
                if finished:
                    lrt.remove(task.task_id)
                if not lrt: #nothing left to listen for
                    return True
        return False

    def is_failed(self):
        is_failed = False
        for task in self.task_list:
           is_failed |= task.task_info['is_failed']
        return is_failed   


class TaskBus(Task):

    task_depth_order = ['J','RS','R','T']

    @classmethod
    def get_type(cls,task_id):
        type,id = task_id.split(':')
        return type

    @classmethod
    def get_depth(cls,ancestor, depth):
        from math import fabs
        desired_depth = cls.task_depth_order.index(ancestor) + depth
        if desired_depth <= len(cls.task_depth_order):
            return desired_depth
        else:
            return len(cls.task_depth_order)

    def __init__(self, task_id, *args, **kw):
        super(TaskBus,self).__init__(None, task_id, *args, **kw)
        self.is_failed = None
        self.update = None
        self.root_elem =  task_id

    def add_print_task_info(self,new_task_info=None):
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
        self.add_print_task_info(task_info)

