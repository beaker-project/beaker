# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import print_function

import sys

import six
import time

__all__ = (
    "TaskWatcher",
    "watch_tasks"
)


def display_tasklist_status(task_list):
    state_dict = {}
    for task in task_list:
        for state, value in six.iteritems(task.get_state_dict()):
            state_dict.setdefault(state, 0)
            state_dict[state] += value
    print("--> " + " ".join(("%s: %s" % (key, state_dict[key])
                             for key in sorted(state_dict)))
          + " [total: %s]" % sum(state_dict.values()))


def watch_tasks(hub, task_id_list, indentation_level=0, sleep_time=30, task_url=None):
    """
    Watch the task statuses until they finish.
    """
    if not task_id_list:
        return
    watcher = TaskWatcher()
    is_failed = False
    try:
        print("Watching tasks (this may be safely interrupted)...")
        for task_id in sorted(task_id_list):
            watcher.task_list.append(Task(hub, task_id, indentation_level))
            # print task url if task_url is set or TASK_URL exists in config file
            task_url = task_url or hub._conf.get("TASK_URL", None)
            if task_url is not None:
                print("Task url: %s" % (task_url % task_id))
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
        running_task_list = [t.task_id for t in watcher.task_list if not watcher.is_finished(t)]
        if running_task_list:
            print("Tasks still running: %s" % running_task_list)
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
        for subtask in six.itervalues(self.subtask_dict):
            result &= subtask.is_finished()
        return result

    def is_failed(self, task):
        """Did the task Fail?"""
        if task.task_info is None:
            return False

        result = task.task_info.get("is_failed", False)
        for subtask in six.itervalues(self.subtask_dict):
            result |= subtask.is_failed()
        return result

    def update(self, task):
        """Update info and log if needed. Returns True on state change."""
        if self.is_finished(task):
            return False

        last = task.task_info
        task.task_info = task.hub.taskactions.task_info(task.task_id, False)

        if task.task_info is None:
            print("No such task id: %s" % task.task_id)
            sys.exit(1)

        changed = False
        state = task.task_info["state"]
        if last:
            # compare and note status changes
            laststate = last["state"]
            if laststate != state:
                print("%s: %s -> %s" % (task, task.display_state(last),
                                        task.display_state(task.task_info)))
                changed = True
        else:
            # first time we're seeing this task, so just show the current state
            print("%s: %s" % (task, task.display_state(task.task_info)))
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
            result += " %s" % self.task_info.get("method", "unknown")
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

        for subtask in six.itervalues(self.subtask_dict):
            for state, value in six.iteritems(subtask.get_state_dict()):
                state_dict.setdefault(state, 0)
                state_dict[state] += value

        return state_dict
