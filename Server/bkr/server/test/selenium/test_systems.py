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

from bkr.server.model import Cpu
from bkr.server.test.selenium import SeleniumTestCase
from bkr.server.test import data_setup
from bkr.server.test.assertions import assert_sorted

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

class TestSystemGridSorting(SeleniumTestCase):

    # tests in this class can safely share the same firefox session
    @classmethod
    def setUpClass(cls):
        try:
            session.begin()
            # ensure we have lots of systems
            for vendor in (u'Acer', u'Dell', u'HP'):
                for model in (u'slow model', u'fast model', u'big model'):
                    for status in (u'Automated', u'Manual', u'Removed'):
                        for type in (u'Machine', u'Virtual', u'Prototype'):
                            for cores in (1, 4):
                                system = data_setup.create_system(
                                    vendor=vendor, model=model,
                                    status=status, type=type)
                                system.user = data_setup.create_user()
                                system.cpu = Cpu(cores=cores)
            session.commit()
        finally:
            session.close()
        cls.selenium = sel = cls.get_selenium()
        sel.start()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()

    # https://bugzilla.redhat.com/show_bug.cgi?id=651418

    def check_column_sort(self, column):
        sel = self.selenium
        sel.click('link=Show all')
        sel.wait_for_page_to_load('30000')
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        cell_values = [sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed
                       for row in range(0, row_count)]
        self.assert_(len(set(cell_values)) > 1) # make sure we're checking something
        assert_sorted(cell_values)

    # We test both ordinary listing (i.e. with no search query) as well as 
    # searching, because they go through substantially different code paths

    def go_to_listing(self):
        self.selenium.open('')

    def go_to_search_results(self):
        sel = self.selenium
        sel.open('')
        sel.click('link=Toggle Search')
        sel.select('systemsearch_0_table', 'CPU/Cores')
        sel.select('systemsearch_0_operation', 'greater than')
        sel.type('systemsearch_0_value', '1')
        sel.click('//form[@name="systemsearch"]//a[text()="Add ( + )"]')
        sel.select('systemsearch_1_table', 'System/Name')
        sel.select('systemsearch_1_operation', 'is not')
        sel.type('systemsearch_1_value', 'bob')
        sel.click('Search')
        sel.wait_for_page_to_load('30000')

    def test_can_sort_listing_by_status(self):
        self.go_to_listing()
        self.check_column_sort(2)

    def test_can_sort_listing_by_vendor(self):
        self.go_to_listing()
        self.check_column_sort(3)

    def test_can_sort_listing_by_model(self):
        self.go_to_listing()
        self.check_column_sort(4)

    def test_can_sort_listing_by_user(self):
        self.go_to_listing()
        self.check_column_sort(6)

    def test_can_sort_listing_by_type(self):
        self.go_to_listing()
        self.check_column_sort(7)

    def test_can_sort_search_results_by_vendor(self):
        self.go_to_search_results()
        self.check_column_sort(2)

    def test_can_sort_search_results_by_user(self):
        self.go_to_search_results()
        self.check_column_sort(3)

    def test_can_sort_search_results_by_type(self):
        self.go_to_search_results()
        self.check_column_sort(4)

    def test_can_sort_search_results_by_status(self):
        self.go_to_search_results()
        self.check_column_sort(5)

    def test_can_sort_search_results_by_model(self):
        self.go_to_search_results()
        self.check_column_sort(7)

    # XXX also test with custom column selections

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
        activity = self.system.activity[-1]
        self.assertEquals(activity.field_name, u'Cc')
        self.assertEquals(activity.service, u'WEBUI')
        self.assertEquals(activity.action, u'Changed')
        self.assertEquals(activity.old_value, u'')
        self.assertEquals(activity.new_value,
                u'roy.baty@pkd.com; deckard@police.gov')

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
        activity = self.system.activity[-1]
        self.assertEquals(activity.field_name, u'Cc')
        self.assertEquals(activity.service, u'WEBUI')
        self.assertEquals(activity.action, u'Changed')
        self.assertEquals(activity.old_value,
                u'deckard@police.gov; roy.baty@pkd.com')
        self.assertEquals(activity.new_value, u'')

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
        activity = self.system.activity[-1]
        self.assertEquals(activity.field_name, u'Cc')
        self.assertEquals(activity.service, u'WEBUI')
        self.assertEquals(activity.action, u'Changed')
        self.assertEquals(activity.old_value, u'roy.baty@pkd.com')
        self.assertEquals(activity.new_value, u'deckard@police.gov')
