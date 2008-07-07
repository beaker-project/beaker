from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from logan.widgets import myPaginateDataGrid
from logan.xmlrpccontroller import RPCRoot
from logan.helpers import make_link
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

    @expose(template='logan.templates.form')
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

    @expose(template='logan.templates.grid')
    @paginate('list',default_order='name', limit=30)
    def index(self, *args, **kw):
        tests = session.query(Test)
        tests_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='name', getter=lambda x: make_link("./%s" % x.id, x.name), title='Name', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='description', getter=lambda x:x.description, title='Description', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='version', getter=lambda x:x.version, title='Version', options=dict(sortable=True)),
                    ])
        return dict(title="Tests", grid=tests_grid, list=tests, search_bar=None)

    @expose(template='logan.templates.test')
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
        test.family_list = 0
        test.arch_list = False
        for family in tinfo.releases:
            test.family_list = 1
            if family.startswith('-'):
                test.family_list = 2
                try:
                    test.families.append(Family.by_name_alias(family.lstrip('-')))
                except exceptions.InvalidRequestError:
                    #FIXME# I think we should import the test anyway and
                    #       report that the scheduler doesn't include that 
                    #       family.
                    pass
                    #raise ValueError('Invalid Family: %s' % family.lstrip('-'))
            else:
                try:
                    test.families.append(Family.by_name_alias(family))
                except exceptions.InvalidRequestError:
                    #FIXME# I think we should import the test anyway and
                    #       report that the scheduler doesn't include that 
                    #       family.
                    pass
                    #raise ValueError('Invalid Family: %s' % family.lstrip('-'))
        for arch in tinfo.test_archs:
            test.arch_list = True
            test.arches.append(Arch.lazy_create(arch=arch))
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

