
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree
import pkg_resources
from turbogears import testutil
from turbogears.database import session
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup, with_transaction, DatabaseTestCase
from bkr.server.model import TaskPackage

class TestJobsController(DatabaseTestCase):

    maxDiff = None

    @with_transaction
    def setUp(self):
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user()
        group = data_setup.create_group(group_name='somegroup')
        group.add_member(self.user)
        testutil.set_identity_user(self.user)
        data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')
        data_setup.create_product(product_name=u'the_product')

    def tearDown(self):
        testutil.set_identity_user(None)

    def test_uploading_job_without_recipeset_raises_exception(self):
        xmljob = lxml.etree.fromstring('''
            <job>
                <whiteboard>job with norecipesets</whiteboard>
            </job>
            ''')
        with session.begin():
            self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))

    def test_uploading_job_with_invalid_hostRequires_raises_exception(self):
        session.begin()
        try:
            xmljob = lxml.etree.fromstring('''
                <job>
                    <whiteboard>job with invalid hostRequires</whiteboard>
                    <recipeSet>
                        <recipe>
                            <distroRequires>
                                <distro_name op="=" value="BlueShoeLinux5-5" />
                            </distroRequires>
                            <hostRequires>
                                <memory op=">=" value="500MB" />
                            </hostRequires>
                            <task name="/distribution/install" role="STANDALONE">
                                <params/>
                            </task>
                        </recipe>
                    </recipeSet>
                </job>
                ''')
            self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))
        finally:
            session.rollback()

    def test_job_xml_can_be_roundtripped(self):
        # Ideally the logic for parsing job XML into a Job instance would live in model code,
        # so that this test doesn't have to go through the web layer...
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'complete-job.xml')
        xmljob = lxml.etree.fromstring(complete_job_xml)
        with session.begin():
            job = testutil.call(self.controller.process_xmljob, xmljob, self.user)
        roundtripped_xml = lxml.etree.tostring(job.to_xml(clone=True), pretty_print=True)
        self.assertMultiLineEqual(roundtripped_xml, complete_job_xml)

    def test_does_not_fail_when_whiteboard_empty(self):
        xml = """
            <job>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5"/>
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </recipe>
                </recipeSet>
            </job>
        """
        xmljob = lxml.etree.fromstring(xml)
        job = self.controller.process_xmljob(xmljob, self.user)
        self.assertEqual(job.whiteboard, u'')

    def test_creates_taskpackages_successfully(self):
        # Note: installPackage is deprecated but we still provide backwards compatibility
        xml = """
        <job>
            <recipeSet>
                <recipe>
                    <distroRequires>
                        <distro_name op="=" value="BlueShoeLinux5-5"/>
                    </distroRequires>
                    <hostRequires/>
                    <installPackage>libbeer</installPackage>
                    <task name="/distribution/install" role="STANDALONE"/>
                </recipe>
            </recipeSet>
        </job>
        """
        xmljob = lxml.etree.fromstring(xml)
        job = self.controller.process_xmljob(xmljob, self.user)
        self.assertListEqual(['libbeer'], [x.package for x in job.recipesets[0].recipes[0].custom_packages])
