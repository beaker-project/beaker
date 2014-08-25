
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from turbogears.database import session
from bkr.server.model import Job
import requests
import lxml.etree
from StringIO import StringIO

class JobExportXML(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.job_to_export = data_setup.create_completed_job()
        self.browser = self.get_browser()

    def test_export_xml(self):
        b = self.browser
        # Make sure the Export button is present in the jobs grid. We can't 
        # actually click it because it triggers a download, which WebDriver 
        # can't handle.
        b.get(get_server_base() + 'jobs/')
        b.find_element_by_name('simplesearch').send_keys(unicode(self.job_to_export.id))
        b.find_element_by_name('jobsearch_simple').submit()
        b.find_element_by_xpath(
                '//tr[normalize-space(string(./td[1]))="%s"]'
                '//a[text()="Export"]'
                % self.job_to_export.t_id)
        # Make sure the Export button is present on the job page.
        b.get(get_server_base() + 'jobs/%s' % self.job_to_export.id)
        b.find_element_by_link_text('Export')
        # Fetch the exported XML directly.
        response = requests.get(get_server_base() +
                'to_xml?taskid=%s&pretty=False' % self.job_to_export.t_id)
        xml_export = response.content
        with session.begin():
            job = Job.by_id(self.job_to_export.id)
            xml_export = job.to_xml().toxml()
            xml_export_tree = lxml.etree.parse(StringIO(xml_export))
            pretty_xml = lxml.etree.tostring(xml_export_tree, pretty_print=False)
            self.assert_(pretty_xml == xml_export)
