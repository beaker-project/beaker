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
import tempfile
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup

class TestNewJob(SeleniumTestCase):

    def setUp(self):
        data_setup.create_distro(name=u'BlueShoeLinux5-5')
        data_setup.create_task(name=u'/distribution/install')
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login()

    def tearDown(self):
        self.selenium.stop()

    def test_warns_about_xsd_validation_errors(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('3000')
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
        sel.wait_for_page_to_load('3000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(sel.get_text('css=.flash'),
                'Job failed XSD validation. Please confirm that you want to submit it.')
        self.assertEqual(int(sel.get_xpath_count('//ul[@class="xsd-error-list"]/li')), 1)
        self.assert_(sel.get_text('//ul[@class="xsd-error-list"]/li').startswith(
                "Line 12, col 0: Element 'brokenElement': This element is not expected."))
        sel.click('//input[@value="Queue despite validation errors"]')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(sel.get_title(), 'Jobs')
        self.assert_(sel.get_text('css=.flash').startswith('Success!'))

    def test_valid_job_xml_doesnt_trigger_xsd_warning(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=New Job')
        sel.wait_for_page_to_load('3000')
        xml_file = tempfile.NamedTemporaryFile()
        xml_file.write('''
            <job>
                <whiteboard>valid job</whiteboard>
                <recipeSet retention_tag="scratch">
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="BlueShoeLinux5-5" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" role="STANDALONE">
                            <params/>
                        </task>
                    </recipe>
                </recipeSet>
            </job>
            ''')
        xml_file.flush()
        sel.type('jobs_filexml', xml_file.name)
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('3000')
        sel.click('//input[@value="Queue"]')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(sel.get_title(), 'Jobs')
        self.assert_(sel.get_text('css=.flash').startswith('Success!'))
