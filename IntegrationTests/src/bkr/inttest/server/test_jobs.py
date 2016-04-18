# coding=utf8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import lxml.etree
import os.path
import pkg_resources
from turbogears import testutil
from turbogears.database import session
from bkr.server.bexceptions import BX
from bkr.inttest import data_setup, with_transaction, DatabaseTestCase
from bkr.server.model import TaskPackage


class TestJobsController(DatabaseTestCase):

    maxDiff = None

    def setUp(self):
        session.begin()
        from bkr.server.jobs import Jobs
        self.controller = Jobs()
        self.user = data_setup.create_user(user_name=u'test-job-owner',
                email_address=u'test-job-owner@example.com')
        group = data_setup.create_group(group_name='somegroup')
        group.add_member(self.user)
        testutil.set_identity_user(self.user)
        data_setup.create_distro_tree(distro_name=u'BlueShoeLinux5-5')
        data_setup.create_product(product_name=u'the_product')
        session.flush()

    def tearDown(self):
        testutil.set_identity_user(None)
        session.rollback()

    def test_uploading_job_without_recipeset_raises_exception(self):
        xmljob = lxml.etree.fromstring('''
            <job>
                <whiteboard>job with norecipesets</whiteboard>
            </job>
            ''')
        self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))

    def test_uploading_job_with_invalid_hostRequires_raises_exception(self):
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

    def test_job_xml_can_be_roundtripped(self):
        # Ideally the logic for parsing job XML into a Job instance would live in model code,
        # so that this test doesn't have to go through the web layer...
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'complete-job.xml')
        xmljob = lxml.etree.fromstring(complete_job_xml)
        job = testutil.call(self.controller.process_xmljob, xmljob, self.user)
        roundtripped_xml = lxml.etree.tostring(job.to_xml(clone=True), pretty_print=True, encoding='utf8')
        self.assertMultiLineEqual(roundtripped_xml, complete_job_xml)

    def test_complete_job_results(self):
        complete_job_xml = pkg_resources.resource_string('bkr.inttest', 'complete-job.xml')
        xmljob = lxml.etree.fromstring(complete_job_xml)
        job = testutil.call(self.controller.process_xmljob, xmljob, self.user)
        session.flush()

        # Complete the job, filling in values to match what's hardcoded in 
        # complete-job-results.xml...
        recipe = job.recipesets[0].recipes[0]
        guestrecipe = recipe.guests[0]
        data_setup.mark_recipe_running(recipe, fqdn=u'system.test-complete-job-results',
                start_time=datetime.datetime(2016, 1, 31, 23, 0, 0),
                install_started=datetime.datetime(2016, 1, 31, 23, 0, 1))
        data_setup.mark_recipe_installation_finished(recipe,
                install_finished=datetime.datetime(2016, 1, 31, 23, 0, 2),
                postinstall_finished=datetime.datetime(2016, 1, 31, 23, 0, 3))
        data_setup.mark_recipe_complete(guestrecipe, fqdn=u'guest.test-complete-job-results',
                mac_address='ff:ff:ff:00:00:00',
                start_time=datetime.datetime(2016, 1, 31, 23, 30, 0),
                install_started=datetime.datetime(2016, 1, 31, 23, 30, 1),
                install_finished=datetime.datetime(2016, 1, 31, 23, 30, 2),
                postinstall_finished=datetime.datetime(2016, 1, 31, 23, 30, 3),
                finish_time=datetime.datetime(2016, 1, 31, 23, 30, 4))
        data_setup.mark_recipe_complete(recipe, only=True,
                start_time=datetime.datetime(2016, 1, 31, 23, 0, 4),
                finish_time=datetime.datetime(2016, 1, 31, 23, 59, 0))
        recipe.installation.rendered_kickstart.url = u'http://example.com/recipe.ks'
        guestrecipe.installation.rendered_kickstart.url = u'http://example.com/guest.ks'
        session.flush()
        # Hack up the database ids... This will fail if it's flushed, but it's 
        # the easiest way to make them match the expected values.
        job.id = 1
        job.recipesets[0].id = 1
        recipe.id = 1
        guestrecipe.id = 2
        recipe.tasks[0].id = 1
        recipe.tasks[1].id = 2
        guestrecipe.tasks[0].id = 3
        guestrecipe.tasks[0].results[0].id = 1
        recipe.tasks[0].results[0].id = 2
        recipe.tasks[1].results[0].id = 3

        expected_results_xml = pkg_resources.resource_string('bkr.inttest', 'complete-job-results.xml')
        actual_results_xml = lxml.etree.tostring(job.to_xml(clone=False),
                pretty_print=True, encoding='utf8')
        self.assertMultiLineEqual(expected_results_xml, actual_results_xml)

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

    def test_upload_xml_catches_invalid_xml(self):
        """We want that invalid Job XML is caught in the validation step."""
        xmljob = lxml.etree.fromstring('''
            <job>
                <whriteboard>job with arbitrary XML in namespaces</whriteboard>
                <recipeSet>
                    <rawcipe>
                        <distroRequires>
                            <distro_name />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE"/>
                    </rawcipe>
                </recipeSet>
            </job>
        ''')
        self.assertRaises(BX, lambda: self.controller.process_xmljob(xmljob, self.user))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1112131
    def test_preserves_arbitrary_XML_elements_in_namespace(self):
        complete_job_xml = pkg_resources.resource_filename('bkr.inttest', 'complete-job.xml')
        with open(complete_job_xml, 'r') as f:
            contents = f.read()
            xmljob = lxml.etree.fromstring(contents)
        job = testutil.call(self.controller.process_xmljob, xmljob, self.user)
        tree = job.to_xml(clone=True)
        self.assertEqual(2, len(tree.xpath('*[namespace-uri()]')))
        self.assertEqual('<b:option xmlns:b="http://example.com/bar">--foobar arbitrary</b:option>',
                         lxml.etree.tostring(tree.xpath('*[namespace-uri()]')[0], encoding='utf8'))
        self.assertEqual(u'<f:test xmlns:f="http://example.com/foo">unicode text: heißer Шис</f:test>'.encode('utf8'),
                         lxml.etree.tostring(tree.xpath('*[namespace-uri()]')[1], encoding='utf8'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1295642
    def test_parses_reservesys(self):
        xmljob = lxml.etree.fromstring('''
            <job>
                <whriteboard>job with reservesys</whriteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires/> <hostRequires/>
                        <task name="/distribution/install"/>
                        <reservesys/>
                    </recipe>
                </recipeSet>
            </job>
        ''')
        job = self.controller.process_xmljob(xmljob, self.user)
        self.assertEqual(job.recipesets[0].recipes[0].reservation_request.duration, 86400)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1295642
    def test_parses_reservesys_with_duration(self):
        xmljob = lxml.etree.fromstring('''
            <job>
                <whriteboard>job with reservesys with duration</whriteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires/> <hostRequires/>
                        <task name="/distribution/install"/>
                        <reservesys duration="600"/>
                    </recipe>
                </recipeSet>
            </job>
        ''')
        job = self.controller.process_xmljob(xmljob, self.user)
        self.assertEqual(job.recipesets[0].recipes[0].reservation_request.duration, 600)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1302857
    def test_strips_whitespace_from_whiteboard(self):
        xmljob = lxml.etree.fromstring('''
            <job>
                <whiteboard>
                    so pretty
                </whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires/> <hostRequires/>
                        <task name="/distribution/install"/>
                    </recipe>
                </recipeSet>
            </job>
        ''')
        job = self.controller.process_xmljob(xmljob, self.user)
        self.assertEqual(job.whiteboard, u'so pretty')
