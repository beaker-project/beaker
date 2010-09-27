#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
import pkg_resources
from turbogears.database import session

class TestSubmitTask(bkr.server.test.selenium.SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login()
    
    def tearDown(self):
        self.selenium.stop()

    def test_submit_task(self):
        test_package_name = '/distribution/beaker/task_test'
        sel = self.selenium
        sel.open('')

        # upload v1.1 first...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('3000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-1.1-0.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('3000')
        # ...and make sure it worked...
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('3000')
        self.assert_task_correct_v1_1()

        # ...then upload v2.0...
        sel.click('link=New Task')
        sel.wait_for_page_to_load('3000')
        sel.type('task_task_rpm',
                pkg_resources.resource_filename(self.__module__,
                'tmp-distribution-beaker-task_test-2.0-2.noarch.rpm'))
        sel.click('//input[@value="Submit Data"]')
        sel.wait_for_page_to_load('3000')
        # ...and make sure everything was updated
        sel.type('simplesearch', test_package_name)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % test_package_name)
        sel.wait_for_page_to_load('3000')
        self.assert_task_correct_v2_0()

    def assert_task_correct_v1_1(self):
        self.assertEqual(self.get_task_info_field('Description'),
                'Fake test for integration testing v1.1')
        self.assertEqual(self.get_task_info_field('Expected Time'), '5 minutes')
        self.assertEqual(self.get_task_info_field('Version'), '1.1-1')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Regression')
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Requires'), 'beaker')

    def assert_task_correct_v2_0(self):
        self.assertEqual(self.get_task_info_field('Description'),
                'Fake test for integration testing v2.0')
        self.assertEqual(self.get_task_info_field('Expected Time'), '30 minutes')
        self.assertEqual(self.get_task_info_field('Version'), '2.0-2')
        self.assertEqual(self.get_task_info_field('License'), 'GPLv2')
        self.assertEqual(self.get_task_info_field('Types'), 'Multihost')
        self.assertEqual(self.get_task_info_field('Run For'), 'beaker')
        self.assertEqual(self.get_task_info_field('Requires'),
                '\n'.join(['beaker', 'rpm', 'coreutils']))

    def get_task_info_field(self, field_label):
        """Returns the value of a field in the task info table."""
        return self.selenium.get_text('//table[@class="show"]'
                '//td[preceding-sibling::td[1]//text()="%s:"]' % field_label)

if __name__ == "__main__":
    unittest.main()
