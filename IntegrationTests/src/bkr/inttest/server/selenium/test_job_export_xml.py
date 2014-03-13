
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from turbogears.database import session
from bkr.server.model import Job
import lxml.etree
from StringIO import StringIO

class JobExportXML(SeleniumTestCase):


    @classmethod
    @with_transaction
    def setupClass(cls):
        cls.password = 'password'
        cls.user = data_setup.create_user(password=cls.password)
        cls.job_to_export = data_setup.create_completed_job(owner=cls.user)
        cls.selenium = cls.get_selenium() 
        cls.selenium.start()

    def test_export_xml(self):
        sel = self.selenium
        sel.open('jobs')
        sel.type("simplesearch", "%s" % self.job_to_export.id)
        sel.click("//a[text()='Export']")
        sel.open('jobs/%s' % self.job_to_export.id)
        sel.click("//a[text()='Export']")
        #make sure it's not pretty print, otherwise it screws things up
        sel.open('to_xml?taskid=%s&to_screen=True&pretty=False' % self.job_to_export.t_id)
        sel.wait_for_page_to_load('30000')
        xml_export = sel.get_text('//body')
        with session.begin():
            job = Job.by_id(self.job_to_export.id)
            xml_export = job.to_xml().toxml()
            xml_export_tree = lxml.etree.parse(StringIO(xml_export))
            pretty_xml = lxml.etree.tostring(xml_export_tree, pretty_print=False)
            self.assert_(pretty_xml == xml_export)


    @classmethod
    def teardownClass(cls):
        cls.selenium.stop()
