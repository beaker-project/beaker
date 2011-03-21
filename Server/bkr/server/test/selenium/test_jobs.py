# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
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

import unittest
import logging
import time
import tempfile
import pkg_resources
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup
from bkr.server.jobs import RetentionTag, Product, Distro

class TestViewJob(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_cc_list(self):
        user = data_setup.create_user(password='password')
        job = data_setup.create_job(owner=user,
                cc=[u'laika@mir.su', u'tereshkova@kosmonavt.su'])
        session.flush()
        sel = self.selenium
        self.login(user=user.user_name, password='password')
        sel.open('')
        sel.click('link=My Jobs')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % job.t_id)
        sel.wait_for_page_to_load('30000')
        self.assert_(sel.get_title().startswith('Job %s' % job.t_id))
        self.assertEqual(
            # value of cell beside "CC" cell
            sel.get_text('//table[@class="show"]//td'
                '[preceding-sibling::td[1]/b/text() = "CC"]'),
            'laika@mir.su; tereshkova@kosmonavt.su')

    def test_edit_job_whiteboard(self):
        user = data_setup.create_user(password='asdf')
        job = data_setup.create_job(owner=user)
        session.flush()
        self.login(user=user.user_name, password='asdf')
        sel = self.selenium
        sel.open('jobs/%s' % job.id)
        sel.wait_for_page_to_load('30000')
        self.assert_(sel.is_editable('name=whiteboard'))
        new_whiteboard = 'new whiteboard value %s' % int(time.time())
        sel.type('name=whiteboard', new_whiteboard)
        sel.click('//form[@id="job_whiteboard_form"]//button[@type="submit"]')
        for i in range(100):
            try:
                if sel.is_element_present('//form[@id="job_whiteboard_form"]//div[@class="msg success"]'): break
            except: pass
            time.sleep(0.2)
        else: self.fail('timed out looking for save success message')
        sel.open('jobs/%s' % job.id)
        self.assertEqual(new_whiteboard, sel.get_value('name=whiteboard'))

class NewJobTest(SeleniumTestCase):

    def setUp(self):
        if not Distro.by_name(u'BlueShoeLinux5-5'):
            data_setup.create_distro(name=u'BlueShoeLinux5-5')
        data_setup.create_task(name=u'/distribution/install')
        data_setup.create_product(product_name=u'the_product')
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_warns_about_xsd_validation_errors(self):
        self.login()
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('30000')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with invalid hostRequires</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                        <brokenElement/>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        sel.type('jobs_filexml', xml_file.name)
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_text('css=.flash'),
                'Job failed schema validation. Please confirm that you want to submit it.')
        self.assert_(int(sel.get_xpath_count('//ul[@class="xsd-error-list"]/li')) > 0)
        sel.click('//input[@value="Queue despite validation errors"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'My Jobs')
        self.assert_(sel.get_text('css=.flash').startswith('Success!'))

    def test_refuses_to_accept_unparseable_xml(self):
        self.login()
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('30000')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with unterminated whiteboard
            </job>
            ''')
        xml_file.flush()
        sel.type('jobs_filexml', xml_file.name)
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('30000')
        self.assert_('Failed to import job' in sel.get_text('css=.flash'))

    def test_valid_job_xml_doesnt_trigger_xsd_warning(self):
        self.login()
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('30000')
        sel.type('jobs_filexml', pkg_resources.resource_filename(
                'bkr.server.test', 'complete-job.xml'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(sel.get_title(), 'My Jobs')
        self.assert_(sel.get_text('css=.flash').startswith('Success!'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=661652
    def test_job_with_excluded_task(self):
        distro = data_setup.create_distro(arch='ia64')
        excluded_task = data_setup.create_task(exclude_arch=[u'ia64'])
        session.flush()
        self.login()
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('30000')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>job with excluded task</whiteboard>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="%s" />
                            <distro_arch op="=" value="ia64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                        <task name="%s" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''' % (distro.name, excluded_task.name))
        xml_file.flush()
        sel.type('jobs_filexml', xml_file.name)
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('30000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('30000')
        flash = sel.get_text('css=.flash')
        self.assert_(flash.startswith('Success!'), flash)
        self.assertEqual(sel.get_title(), 'My Jobs')

class CloneJobTest(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_cloning_recipeset_from_job_with_product(self):
        job = data_setup.create_job()
        job.retention_tag = RetentionTag.list_by_requires_product()[0]
        job.product = Product(u'product_name')
        session.flush()
        self.login()
        sel =  self.selenium
        sel.open('jobs/clone?job_id=%s' % job.id)
        sel.wait_for_page_to_load('30000')
        cloned_from_job = sel.get_text('//textarea[@id="job_textxml"]')
        sel.open('jobs/clone?recipeset_id=%s' % job.recipesets[0].id)
        sel.wait_for_page_to_load('30000')
        cloned_from_rs = sel.get_text('//textarea[@id="job_textxml"]')
        self.assertEqual(cloned_from_job,cloned_from_rs)

    def test_cloning_recipeset(self):
        job = data_setup.create_job()
        session.flush()
        self.login()
        sel = self.selenium
        sel.open('jobs/clone?job_id=%s' % job.id)
        sel.wait_for_page_to_load('30000')
        cloned_from_job = sel.get_text('//textarea[@id="job_textxml"]')
        sel.open('jobs/clone?recipeset_id=%s' % job.recipesets[0].id)
        sel.wait_for_page_to_load('30000')
        cloned_from_rs = sel.get_text('//textarea[@id="job_textxml"]')
        self.assertEqual(cloned_from_job, cloned_from_rs)
