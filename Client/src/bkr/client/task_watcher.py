# -*- coding: utf-8 -*-


import sys
import time


__all__ = (
    "TaskWatcher",
    "watch_tasks",
)


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
