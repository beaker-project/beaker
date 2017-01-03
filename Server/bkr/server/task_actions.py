
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
XML-RPC methods in the :mod:`taskactions` namespace can be applied to a running 
job or any of its constituent parts (recipe sets, recipes, tasks, and task 
results). For methods related to Beaker's task library, see the 
:ref:`task-library` section.

These methods accept a *taskid* argument, which must be a string of the form 
*type*:*id*, for example ``'RS:4321'``. The server recognises the following 
values for *type*:

* J: Job
* RS: Recipe set
* R: Recipe
* T: Task within a recipe
* TR: Result within a task
"""

import lxml.etree
from sqlalchemy.exc import InvalidRequestError
from bkr.server import identity
from bkr.server.model import (Job, RecipeSet, Recipe,
                              RecipeTask, RecipeTaskResult, TaskBase)
from bkr.server.bexceptions import BX, StaleTaskStatusException
from bkr.server.xmlrpccontroller import RPCRoot
import cherrypy

__all__ = ['TaskActions']

class TaskActions(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
    unstoppable_task_types = [Recipe, RecipeTaskResult]

    task_types = dict(J  = Job,
                      RS = RecipeSet,
                      R  = Recipe,
                      T  = RecipeTask,
                      TR = RecipeTaskResult)

    stoppable_task_types = dict([(rep, obj) for rep,obj in task_types.iteritems() if obj not in unstoppable_task_types])

    @cherrypy.expose
    def task_info(self, taskid,flat=True):
        """
        Returns an XML-RPC structure (dict) describing the current state of the 
        given job component.

        :param taskid: see above
        :type taskid: string
        """
        return TaskBase.get_by_t_id(taskid).task_info()

    @cherrypy.expose
    def to_xml(self, taskid, clone=False, exclude_enclosing_job=True, include_logs=True):
        """
        Returns an XML representation of the given job component, including its 
        current state.

        :param taskid: see above
        :type taskid: string
        :param clone: If True, returns XML suitable for submitting back to 
            Beaker. Otherwise, the XML includes results.
        :type clone: bool
        :param exclude_enclosing_job: If False, returns <job> as the root 
            element even when requesting a recipe set or recipe. This is useful 
            when cloning, in order to always produce a complete job definition.
        :type exclude_enclosing_job: bool
        :param include_logs: If True (the default), the results XML includes 
            links to all logs. This can make the results XML substantially larger.
        :type include_logs: bool
        """
        task_type, task_id = taskid.split(":")
        if task_type.upper() in self.task_types.keys():
            try:
                task = self.task_types[task_type.upper()].by_id(task_id)
            except InvalidRequestError:
                raise BX(_("Invalid %s %s" % (task_type, task_id)))
        return lxml.etree.tostring(
                task.to_xml(clone=clone,
                            include_enclosing_job=not exclude_enclosing_job,
                            include_logs=include_logs),
                xml_declaration=False, encoding='UTF-8')

    @cherrypy.expose
    def files(self, taskid):
        """
        Returns an array of XML-RPC structures (dicts) describing each of the 
        result files for the given job component and its descendants.

        :param taskid: see above
        :type taskid: string
        """
        return [l.dict for l in TaskBase.get_by_t_id(taskid).all_logs()]

    @identity.require(identity.not_anonymous())
    @cherrypy.expose
    def stop(self, taskid, stop_type, msg):
        """
        Cancels the given job. Note that when cancelling some part of a job 
        (for example, by passing *taskid* starting with ``R:`` to indicate 
        a particular recipe within a job) the entire job is cancelled.

        :param taskid: see above
        :type taskid: string
        :param stop_type: must be ``'cancel'`` (other values are reserved for 
            Beaker's internal use)
        :type stop_type: string
        :param msg: reason for cancelling
        :type msg: string
        """
        task_type, task_id = taskid.split(":")
        if task_type.upper() in self.stoppable_task_types.keys():
            try:
                task = self.stoppable_task_types[task_type.upper()].by_id(int(task_id))
            except (InvalidRequestError, ValueError):
                raise BX(_("Invalid %s %s" % (task_type, task_id)))
        else:
            raise BX(_("Task type %s is not stoppable" % (task_type)))
        if stop_type not in task.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, task.stop_types)))
        if not task.can_stop(identity.current.user):
            raise BX(_("You don't have permission to %s %s" % (stop_type,
                                                               taskid)))
        kwargs = dict(msg = msg)
        task.record_activity(user=identity.current.user, service=u'XMLRPC',
                             field=u'Status', action=u'Cancelled', old='', new='')
        try:
            return getattr(task, stop_type)(**kwargs)
        except StaleTaskStatusException:
            raise BX(_(u"Could not cancel job id %s. Please try later" % task_id))

# for sphinx
taskactions = TaskActions
