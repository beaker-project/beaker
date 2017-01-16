
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

    maxDiff = None

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
        b.find_element_by_name('simplesearch').send_keys(unicode(self.job_to_export.whiteboard))
        b.find_element_by_name('jobsearch_simple').submit()
        b.find_element_by_xpath(
                '//tr[normalize-space(string(./td[1]))="%s"]'
                '//a[text()="Export"]'
                % self.job_to_export.t_id)
        # Fetch the exported XML directly.
        response = requests.get(get_server_base() +
                'to_xml?taskid=%s&pretty=False' % self.job_to_export.t_id)
        actual = response.content
        with session.begin():
            # Expire the job, otherwise the exported job XML (read from the
            # Python instance) will have a duration attribute while the export
            # from the view will have not since our database stores only seconds
            session.expire_all()
            job = Job.by_id(self.job_to_export.id)
            expected = lxml.etree.tostring(job.to_xml(), pretty_print=True, encoding='utf8')
            self.assertMultiLineEqual(expected, actual)
