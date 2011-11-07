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
from turbogears.database import session

from bkr.server.model import Job
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
from bkr.inttest.assertions import assert_sorted

class TestRecipesDataGrid(SeleniumTestCase):

    log = logging.getLogger(__name__ + '.TestRecipesIndex')

    # tests in this class can safely share the same firefox session
    @classmethod
    def setUpClass(cls):
        # create a bunch of jobs
        cls.user = user = data_setup.create_user(password='password')
        arches = [u'i386', u'x86_64', u'ia64']
        distro_names = [u'DAN5-Server-U5', u'DAN5-Client-U5',
                u'DAN6-Server-U1', u'DAN6-Server-RC3']
        for arch in arches:
            for distro_name in distro_names:
                distro = data_setup.create_distro(name=distro_name, arch=arch)
                data_setup.create_job(owner=user, distro=distro)
                data_setup.create_completed_job(owner=user, distro=distro)
        session.flush()

        # XXX we could save a *lot* of time by reusing Firefox instances across tests
        cls.selenium = sel = cls.get_selenium()
        sel.start()

        # log in
        sel.open('')
        sel.click('link=Login')
        sel.wait_for_page_to_load('30000')
        sel.type('user_name', user.user_name)
        sel.type('password', 'password')
        sel.click('login')
        sel.wait_for_page_to_load('30000')

    @classmethod
    def tearDownClass(cls):
        cls.selenium.stop()

    # see https://bugzilla.redhat.com/show_bug.cgi?id=629147
    def check_column_sort(self, column):
        sel = self.selenium
        sel.open('recipes/mine')
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
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
        sel.open('recipes/mine')
        sel.click('//table[@id="widget"]/thead/th[%d]//a[@href]' % column)
        sel.wait_for_page_to_load('30000')
        row_count = int(sel.get_xpath_count(
                '//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = []
        for row in range(0, row_count):
            raw_value = sel.get_table('widget.%d.%d' % (row, column - 1)) # zero-indexed
            m = re.match(r'R:(\d+)$', raw_value)
            assert m.group(1)
            cell_values.append(int(m.group(1)))
        assert_sorted(cell_values)

class TestRecipeView(SeleniumTestCase):

    def setUp(self):
        self.user = user = data_setup.create_user(display_name=u'Bob Brown',
                password='password')
        self.system_owner = data_setup.create_user()
        self.system = data_setup.create_system(owner=self.system_owner, arch=u'x86_64')
        distro = data_setup.create_distro(arch=u'x86_64')
        self.job = data_setup.create_completed_job(owner=user, distro=distro, server_log=True)
        for recipe in self.job.all_recipes:
            recipe.system = self.system
        session.flush()
        self.selenium = sel = self.get_selenium()
        self.selenium.start()

        # log in
        sel.open('')
        sel.click('link=Login')
        sel.wait_for_page_to_load('30000')
        sel.type('user_name', user.user_name)
        sel.type('password', 'password')
        sel.click('login')
        sel.wait_for_page_to_load('30000')

    def tearDown(self):
        self.selenium.stop()

    # https://bugzilla.redhat.com/show_bug.cgi?id=623603
    # see also TestSystemView.test_can_report_problem
    def test_can_report_problem(self):
        sel = self.selenium
        sel.open('recipes/mine')
        recipe = list(self.job.all_recipes)[0]
        sel.click('link=R:%s' % recipe.id)
        sel.wait_for_page_to_load('30000')
        sel.click('link=Report problem with system')
        sel.wait_for_page_to_load('30000')
        self.assertEqual(self.selenium.get_title(),
                'Report a problem with %s' % self.system.fqdn)

    def test_log_url_looks_right(self):
        sel = self.selenium
        some_job = self.job
        r = some_job.recipesets[0].recipes[0]
        sel.open('recipes/%s' % r.id)
        sel.wait_for_page_to_load('30000')
        sel.click("all_recipe_%s" % r.id)
        from time import sleep
        sleep(2)
        rt_log_server_link = sel.get_attribute("//tr[@class='even pass_recipe_%s recipe_%s']//td[position()=4]//a@href" % (r.id, r.id))
        rt_log = r.tasks[0].logs[0]
        self.assert_(rt_log_server_link == rt_log.server + '/' + rt_log.filename)
        sel.click("logs_button_%s" % r.id)
        sleep(2)
        r_server_link = sel.get_attribute("//table[@class='show']/tbody//tr[position()=6]/td/a@href")
        self.assert_(r_server_link == r.logs[0].server + '/' + r.logs[0].filename)
