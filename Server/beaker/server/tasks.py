#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, config
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import make_link
from sqlalchemy import exceptions
from subprocess import *
import testinfo
import rpm
import os

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

class Tasks(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    task_dir = config.get("basepath.rpms", "/tmp")

    upload = widgets.FileField(name='task_rpm', label='Task rpm')
    form = widgets.TableForm(
        'task',
        fields = [upload],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

    @expose(template='beaker.server.templates.form-post')
    def new(self, **kw):
        return dict(
            title = 'New Task',
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @cherrypy.expose
    def upload(self, task_rpm_name, task_rpm_data):
        """
        XMLRPC method to upload task rpm package
        """
        rpm_file = "%s/%s" % (self.task_dir, task_rpm_name)
        FH = open(rpm_file, "w")
        FH.write(task_rpm_data.data)
        FH.close()
        try:
            task = self.process_taskinfo(self.read_taskinfo(rpm_file))
        except ValueError, err:
            session.rollback()
            return (0, "Failed to import because of %s" % str(err))
        os.chdir(self.task_dir)
        os.system("createrepo .")
        return (task.id, 'Success')

    @expose()
    def save(self, task_rpm, *args, **kw):
        """
        TurboGears method to upload task rpm package
        """
        rpm_file = "%s/%s" % (self.task_dir, task_rpm.filename)

        rpm = task_rpm.file.read()
        FH = open(rpm_file, "w")
        FH.write(rpm)
        FH.close()

        try:
            task = self.process_taskinfo(self.read_taskinfo(rpm_file))
        except ValueError, err:
            session.rollback()
            flash(_(u'Failed to import because of %s' % err ))
            redirect(".")
        os.chdir(self.task_dir)
        os.system("createrepo .")

        flash(_(u"%s Added/Updated at id:%s" % (task.name,task.id)))
        redirect(".")

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='name', limit=30)
    def index(self, *args, **kw):
        tasks = session.query(Task)
        tasks_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='name', getter=lambda x: make_link("./%s" % x.id, x.name), title='Name', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='description', getter=lambda x:x.description, title='Description', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='version', getter=lambda x:x.version, title='Version', options=dict(sortable=True)),
                    ])
        return dict(title="Tasks", grid=tasks_grid, list=tasks, search_bar=None)

    @expose(template='beaker.server.templates.task')
    def default(self, *args, **kw):
        task = Task.by_id(args[0])
        return dict(task=task)

    def process_taskinfo(self, raw_taskinfo):
        tinfo = testinfo.parse_string(raw_taskinfo['desc'])

        task = Task.lazy_create(name=tinfo.test_name)
        # Remove old RPM
        if task.rpm and task.rpm != raw_taskinfo['hdr']['rpm']:
            try:
                os.unlink("%s/%s" % (self.task_dir, task.rpm))
            except OSError, err:
                raise BX(_(err))   
        task.rpm = raw_taskinfo['hdr']['rpm']
        task.version = raw_taskinfo['hdr']['ver']
        task.description = tinfo.test_description
        task.bugzillas = []
        task.required = []
        task.runfor = []
        task.needs = []
        for family in tinfo.releases:
            if family.startswith('-'):
                try:
                    if TaskExclude(task=task,osmajor=osmajor.by_name(family.lstrip('-'))) not in task.excluded:
                        task.excluded.append(TaskExclude(osmajor=osmajor.by_name(family.lstrip('-'))))
                except exceptions.InvalidRequestError:
                    pass
        if tinfo.test_archs:
            arches = set([ '%s' % arch.arch for arch in Arch.query()])
            for arch in arches.difference(set(tinfo.test_archs)):
                task.excluded.append(TaskExclude(arch=Arch.by_name(arch)))
        task.avg_time = tinfo.avg_test_time
        for type in tinfo.types:
            task.types.append(TaskType.lazy_create(type=type))
        for bug in tinfo.bugs:
            task.bugzillas.append(TaskBugzilla(bugzilla_id=bug))
        task.path = tinfo.test_path
        for runfor in tinfo.runfor:
            task.runfor.append(TaskPackage.lazy_create(package=runfor))
        for require in tinfo.requires:
            task.required.append(TaskPackage.lazy_create(package=require))
        for need in tinfo.needs:
            task.needs.append(TaskPropertyNeeded(property=need))
        task.license = tinfo.license

        return task

    def read_taskinfo(self, rpm_file):
        taskinfo = {}
        taskinfo['hdr'] = self.get_rpm_info(rpm_file)
        taskinfo_file = None
	for file in taskinfo['hdr']['files']:
            if file.endswith('testinfo.desc'):
                taskinfo_file = file
        if taskinfo_file:
            p1 = Popen(["rpm2cpio", rpm_file], stdout=PIPE)
            p2 = Popen(["cpio", "--extract" , "--to-stdout", ".%s" % taskinfo_file], stdin=p1.stdout, stdout=PIPE)
            taskinfo['desc'] = p2.communicate()[0]
        return taskinfo

    def get_rpm_info(self, rpm_file):
        """Returns rpm information by querying a rpm"""
        ts = rpm.ts()
        fdno = os.open(rpm_file, os.O_RDONLY)
        try:
            hdr = ts.hdrFromFdno(fdno)
        except rpm.error:
            fdno = os.open(rpm_file, os.O_RDONLY)
            ts.setVSFlags(rpm._RPMVSF_NOSIGNATURES)
            hdr = ts.hdrFromFdno(fdno)
        os.close(fdno)
        return { 'name': hdr[rpm.RPMTAG_NAME], 
                 'ver' : "%s-%s" % (hdr[rpm.RPMTAG_VERSION],
                                    hdr[rpm.RPMTAG_RELEASE]), 
                 'epoch': hdr[rpm.RPMTAG_EPOCH],
                 'arch': hdr[rpm.RPMTAG_ARCH] , 
                 'rpm': "%s" % rpm_file.split('/')[-1:][0],
                 'files': hdr['filenames']}

