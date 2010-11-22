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
from turbogears.database import session

from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup

class TestSystemView(SeleniumTestCase):

    slow = True

    def setUp(self):
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner)
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def go_to_system_view(self):
        sel = self.selenium
        sel.open('')
        sel.type('simplesearch', self.system.fqdn)
        sel.click('search')
        sel.wait_for_page_to_load('3000')
        sel.click('link=%s' % self.system.fqdn)
        sel.wait_for_page_to_load('3000')

    # https://bugzilla.redhat.com/show_bug.cgi?id=631421
    def test_page_title_shows_fqdn(self):
        self.go_to_system_view()
        self.assertEquals(self.selenium.get_title(), self.system.fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=623603
    # see also TestRecipeView.test_can_report_problem
    def test_can_report_problem(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click('link=(Report problem)')
        sel.wait_for_page_to_load('3000')
        self.assertEqual(self.selenium.get_title(),
                'Report a problem with %s' % self.system.fqdn)

    def test_links_to_cc_change(self):
        self.login()
        sel = self.selenium
        self.go_to_system_view()
        sel.click( # link inside cell beside "Notify CC" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::th[1]/label/text())="Notify CC"]'
                '/a[text()="(Change)"]')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(self.selenium.get_title(),
                'Notify CC list for %s' % self.system.fqdn)

class SystemCcTest(SeleniumTestCase):

    def setUp(self):
        user = data_setup.create_user(password=u'swordfish')
        self.system = data_setup.create_system(owner=user)
        session.flush()
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.login(user=user.user_name, password='swordfish')

    def tearDown(self):
        self.selenium.stop()

    def test_add_email_addresses(self):
        self.system.cc = []
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        assert not sel.get_value('cc_cc_0_email_address'), 'should be empty'
        sel.type('cc_cc_0_email_address', 'roy.baty@pkd.com')
        sel.click('doclink') # why the hell is it called this?
        sel.type('cc_cc_1_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
        session.refresh(self.system)
        self.assertEquals(set(self.system.cc),
                set([u'roy.baty@pkd.com', u'deckard@police.gov']))

    def test_remove_email_addresses(self):
        self.system.cc = [u'roy.baty@pkd.com', u'deckard@police.gov']
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.click('//tr[@id="cc_cc_1"]//a[text()="Remove (-)"]')
        #sel.click('//tr[@id="cc_cc_0"]//a[text()="Remove (-)"]')
        # The tg_expanding_widget javascript doesn't let us remove the last element,
        # so we have to just clear it instead :-S
        sel.type('cc_cc_0_email_address', '')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
        session.refresh(self.system)
        self.assertEquals(self.system.cc, [])

    def test_replace_existing_email_address(self):
        self.system.cc = [u'roy.baty@pkd.com']
        session.flush()
        sel = self.selenium
        sel.open('cc_change?system_id=%s' % self.system.id)
        sel.type('cc_cc_0_email_address', 'deckard@police.gov')
        sel.click('//input[@value="Change"]')
        sel.wait_for_page_to_load('30000')
        session.refresh(self.system)
        self.assertEquals(self.system.cc, [u'deckard@police.gov'])
