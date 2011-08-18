#!/usr/bin/python

import sys
import os.path
import datetime
from turbogears.database import session
from bkr.server.util import load_config, log_to_stream
from bkr.server.model import Task
from bkr.server import testinfo

def populate(task):
    from bkr.server.tasks import Tasks
    controller = Tasks()
    filename = os.path.join(controller.task_dir, task.rpm)
    if not os.path.exists(filename):
        print 'Skipping missing %s' % filename
        return
    raw_taskinfo = controller.read_taskinfo(filename)
    tinfo = testinfo.parse_string(raw_taskinfo['desc'], raise_errors=False)
    if tinfo.owner:
        task.owner = tinfo.owner.decode('utf8')
    if tinfo.priority:
        task.priority = tinfo.priority.decode('utf8')
    task.destructive = tinfo.destructive

if __name__ == '__main__':
    load_config()
    log_to_stream(sys.stderr)
    session.begin()
    for task in Task.query.filter(Task.valid == True):
        populate(task)
    session.commit()
