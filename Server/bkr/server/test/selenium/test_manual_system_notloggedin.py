#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session, get_engine

class NotLoggedInManualSystem(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        self.system = data_setup.create_system(status=u'Manual')
        self.system.shared = True
        self.group = data_setup.create_group()
        data_setup.add_group_to_system(self.system,self.group)
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()
        session.flush()

    def test_can_view_system(self):
        sel = self.selenium
        sel.open(u'/view/%s' % self.system.fqdn) #Testing that this does not throw ISE

    def tearDown(self):
        self.selenium.stop()
