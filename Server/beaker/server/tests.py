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
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import make_link
from sqlalchemy import exceptions

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

class Tests(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    test_dir = '/tmp'

    upload = widgets.FileField(name='test_rpm', label='Test rpm')
    form = widgets.TableForm(
        'test',
        fields = [upload],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

    @expose(template='beaker.server.templates.form-post')
    def new(self, **kw):
        return dict(
            title = 'New Test',
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @cherrypy.expose
    def upload(self, test_rpm_name, test_rpm_data):
        """
        XMLRPC method to upload test rpm package
        """
        rpm_file = "%s/%s" % (self.test_dir, test_rpm_name)
        print "rpm_file = %s" % rpm_file
        FH = open(rpm_file, "w")
        FH.write(test_rpm_data.data)
        FH.close()
        try:
            test = self.process_testinfo(self.read_testinfo(rpm_file))
        except ValueError, err:
            session.rollback()
            return (0, "Failed to import because of %s" % str(err))
        session.save_or_update(test)
        session.flush()
        return (test.id, 'Success')

    @expose()
    def save(self, test_rpm, *args, **kw):
        """
        TurboGears method to upload test rpm package
        """
        rpm_file = "%s/%s" % (self.test_dir, test_rpm.filename)

        rpm = test_rpm.file.read()
        FH = open(rpm_file, "w")
        FH.write(rpm)
        FH.close()

        try:
            test = self.process_testinfo(self.read_testinfo(rpm_file))
        except ValueError, err:
            session.rollback()
            flash(_(u'Failed to import because of %s' % err ))
            redirect(".")
        session.save_or_update(test)
        session.flush()

        flash(_(u"%s Added/Updated at id:%s" % (test.name,test.id)))
        redirect(".")

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='name', limit=30)
    def index(self, *args, **kw):
        tests = session.query(Test)
        tests_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='name', getter=lambda x: make_link("./%s" % x.id, x.name), title='Name', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='description', getter=lambda x:x.description, title='Description', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='version', getter=lambda x:x.version, title='Version', options=dict(sortable=True)),
                    ])
        return dict(title="Tests", grid=tests_grid, list=tests, search_bar=None)

    @expose(template='beaker.server.templates.test')
    def default(self, *args, **kw):
        test = Test.by_id(args[0])
        return dict(test=test)

    def process_testinfo(self, raw_testinfo):
        import testinfo
        tinfo = testinfo.parse_string(raw_testinfo['desc'])

        test = Test.lazy_create(name=tinfo.test_name)
        test.rpm = raw_testinfo['hdr']['rpm']
        test.version = raw_testinfo['hdr']['ver']
        test.description = tinfo.test_description
        test.bugzillas = []
        test.required = []
        test.runfor = []
        test.needs = []
        for family in tinfo.releases:
            if family.startswith('-'):
                try:
                    if TestExclude(test=test,osmajor=osmajor.by_name(family.lstrip('-'))) not in test.excluded:
                        test.excluded.append(TestExclude(osmajor=osmajor.by_name(family.lstrip('-'))))
                except exceptions.InvalidRequestError:
                    pass
        if tinfo.test_archs:
            arches = set([ '%s' % arch.arch for arch in Arch.query()])
            for arch in arches.difference(set(tinfo.test_archs)):
                test.excluded.append(TestExclude(arch=Arch.by_name(arch)))
        test.avg_time = tinfo.avg_test_time
        for type in tinfo.types:
            test.types.append(TestType.lazy_create(type=type))
        for bug in tinfo.bugs:
            test.bugzillas.append(TestBugzilla(bugzilla_id=bug))
        test.path = tinfo.test_path
        for runfor in tinfo.runfor:
            test.runfor.append(TestPackage.lazy_create(package=runfor))
        for require in tinfo.requires:
            test.required.append(TestPackage.lazy_create(package=require))
        for need in tinfo.needs:
            test.needs.append(TestPropertyNeeded(property=need))
        test.license = tinfo.license

        return test

    def read_testinfo(self, rpm_file):
        from subprocess import *
        testinfo = {}
        testinfo['hdr'] = self.get_rpm_info(rpm_file)
        testinfo_file = None
	for file in testinfo['hdr']['files']:
            if file.endswith('testinfo.desc'):
                testinfo_file = file
        if testinfo_file:
            p1 = Popen(["rpm2cpio", rpm_file], stdout=PIPE)
            p2 = Popen(["cpio", "--extract" , "--to-stdout", ".%s" % testinfo_file], stdin=p1.stdout, stdout=PIPE)
            testinfo['desc'] = p2.communicate()[0]
        return testinfo

    def get_rpm_info(self, rpm_file):
        import rpm
        import os
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

