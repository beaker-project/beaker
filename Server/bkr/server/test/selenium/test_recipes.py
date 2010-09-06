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
import re
from selenium import selenium

def assert_sorted(things):
    if len(things) == 0: return
    for n in xrange(1, len(things)):
        if things[n] < things[n - 1]:
            raise AssertionError('Not in sorted order, found %r after %r' %
                    (things[n], things[n - 1]))

class TestRecipesIndex(unittest.TestCase):

    slow = True
    log = logging.getLogger('bkr.server.seleniumtests.test_recipes.TestRecipesIndex')

    def setUp(self):
        # XXX we could save a *lot* of time by reusing Firefox instances across tests
        self.selenium = selenium('localhost', 4444, '*chrome', 'http://localhost:8080/')
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    # see https://bugzilla.redhat.com/show_bug.cgi?id=629147

    def check_column_sort(self, column):
        sel = self.selenium
        sel.open('recipes/')
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 50)
        cell_values = [sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed
                       for row in range(0, row_count)]
        assert_sorted(cell_values)

    def test_can_sort_by_whiteboard(self):
        self.check_column_sort(2)

    def test_can_sort_by_arch(self):
        self.check_column_sort(3)

    def test_can_sort_by_system(self):
        self.check_column_sort(4)

    def test_can_sort_by_distro(self):
        self.check_column_sort(5)

    def test_can_sort_by_status(self):
        self.check_column_sort(7)

    def test_can_sort_by_result(self):
        self.check_column_sort(8)

    # this version is different since the cell values will be like ['R:1', 'R:10', ...]
    def test_can_sort_by_id(self):
        column = 1
        sel = self.selenium
        sel.open('recipes/')
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 50)
        cell_values = []
        for row in range(0, row_count):
            raw_value = sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed
            m = re.match(r'R:(\d+)$', raw_value)
            assert m.group(1)
            cell_values.append(int(m.group(1)))
        assert_sorted(cell_values)
