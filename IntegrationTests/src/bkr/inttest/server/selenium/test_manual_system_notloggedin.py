#!/usr/bin/python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
import unittest, time, re, os
from turbogears.database import session, get_engine

class NotLoggedInManualSystem(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system(status=u'Manual')
        self.group = data_setup.create_group()
        data_setup.add_group_to_system(self.system,self.group)
        self.verificationErrors = []
        self.selenium = self.get_selenium()
        self.selenium.start()

    def test_can_view_system(self):
        sel = self.selenium
        sel.open(u'/view/%s' % self.system.fqdn) #Testing that this does not throw ISE

    def tearDown(self):
        self.selenium.stop()
