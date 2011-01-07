#!/usr/bin/python

import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session

class Cancel(bkr.server.test.selenium.SeleniumTestCase):

    def setUp(self):
        self.job = data_setup.create_job()
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_cancel_recipeset(self):
        sel = self.selenium
        self.login()
        sel.open('jobs/%s' % self.job.id)
        sel.wait_for_page_to_load("30000")
        #sel.click("(//a[text()='Cancel'])[last()]")
        sel.click("//div[@id='fedora-content']/div[3]/div[1]/div/table/tbody/tr/td[7]/div/a[1]")
        sel.wait_for_page_to_load("30000")
        sel.click("//input[@value='Yes']")
        sel.wait_for_page_to_load("30000")
        
        self.assertTrue(sel.is_text_present("Successfully cancelled recipeset %s" % self.job.recipesets[0].id))

    def tearDown(self):
        self.selenium.stop()
