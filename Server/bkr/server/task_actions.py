from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from model import *
from turbogears import identity, redirect, config
from cherrypy import request, response
from cherrypy.lib.cptools import serve_file
from bexceptions import *
from bkr.server.xmlrpccontroller import RPCRoot

from kid import Element
import cherrypy
import md5

# for debugging
import sys

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
import breadcrumbs
from datetime import datetime

class TaskActions(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    task_types = dict(J  = Job,
                      RS = RecipeSet,
                      R  = Recipe,
                      T  = RecipeTask,
                      TR = RecipeTaskResult)

    @cherrypy.expose
    def task_info(self, taskid, flat=True):
        """
        XMLRPC method to get task status
        """
        task_type, task_id = taskid.split(":")
        if task_type.upper() in self.task_types.keys():
            try:
                task = self.task_types[task_type.upper()].by_id(task_id)
            except InvalidRequestError, e:
                raise BX(_("Invalid %s %s" % (task_type, task_id)))
        return task.task_info()

    @cherrypy.expose
    def to_xml(self, taskid):
        """
        XMLRPC method to get xml of Job/RecipeSet/Recipe/etc..
        """
        task_type, task_id = taskid.split(":")
        if task_type.upper() in self.task_types.keys():
            try:
                task = self.task_types[task_type.upper()].by_id(task_id)
            except InvalidRequestError, e:
                raise BX(_("Invalid %s %s" % (task_type, task_id)))
        return task.to_xml().toprettyxml()

    @cherrypy.expose
    def stop(self, taskid, stop_type, msg):
        """
        XMLRPC method to cancel/abort a Job/RecipeSet/Recipe/etc..
        """
        task_type, task_id = taskid.split(":")
        if task_type.upper() in self.task_types.keys():
            try:
                task = self.task_types[task_type.upper()].by_id(task_id)
            except InvalidRequestError, e:
                raise BX(_("Invalid %s %s" % (task_type, task_id)))
        if stop_type not in task.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, task.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(task,stop_type)(**kwargs)

