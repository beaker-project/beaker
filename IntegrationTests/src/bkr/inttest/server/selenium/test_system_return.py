
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from turbogears.database import session
from bkr.server.model import SystemStatus, TaskStatus
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest.server.requests_utils import login as requests_login, put_json


class SystemReturnTestWD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_cannot_return_running_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_running(recipe)
            system = recipe.resource.system
        b = self.browser
        login(b)
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        # "Return" button should be absent
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")'
                ' and not(.//a[text()="Return"])]')
        # try doing it directly
        s = requests.Session()
        requests_login(s)
        response = put_json(get_server_base() +
                'systems/%s/reservations/+current' % system.fqdn,
                session=s, data=dict(finish_time='now'))
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text, 'Cannot return system with running %s' % recipe.t_id)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1007789
    def test_can_return_manual_reservation_when_automated(self):

        with session.begin():
            user = data_setup.create_user(password='foobar')
            system = data_setup.create_system(owner=user, status=SystemStatus.manual)

        b = self.browser
        login(b, user=user.user_name, password="foobar")

        # Take
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Take').click()
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")]'
                '//span[@class="label" and text()="Reserved"]')

        # toggle status to Automated
        with session.begin():
            system.lab_controller = data_setup.create_labcontroller()
            system.status = SystemStatus.automated

        # Attempt to return
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Return').click()
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")]'
                '//span[@class="label" and text()="Idle"]')

    def test_cant_return_sneakily(self):
        with session.begin():
            system = data_setup.create_system(shared=True,
                    status=SystemStatus.manual)
            user = data_setup.create_user(password=u'password')
        b = self.browser
        login(b) #login as admin
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Take').click()
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")]'
                '//span[@class="label" and text()="Reserved"]')

        # Test for https://bugzilla.redhat.com/show_bug.cgi?id=747328
        s = requests.Session()
        requests_login(s, user.user_name, 'password')
        response = put_json(get_server_base() +
                'systems/%s/reservations/+current' % system.fqdn,
                session=s, data=dict(finish_time='now'))
        self.assertEquals(response.status_code, 403)
        self.assertIn('Cannot return system', response.text)

    def test_return_with_no_lc(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(shared=True,
                    status=SystemStatus.manual, lab_controller=lc)
            user = data_setup.create_user(password=u'password')
        b = self.browser
        login(b, user.user_name, 'password')
        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Take').click()
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")]'
                '//span[@class="label" and text()="Reserved"]')

        # Let's remove the LC
        with session.begin():
            system.lc = None

        b.get(get_server_base() + 'view/%s' % system.fqdn)
        b.find_element_by_link_text('Return').click()
        b.find_element_by_xpath('//div[contains(@class, "system-quick-usage")]'
                '//span[@class="label" and text()="Idle"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1102442
    def test_system_reserved_on_recipe(self):
        with session.begin():
            user = data_setup.create_user(password=u'password')
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(owner=user, lab_controller=lc)
            recipe = data_setup.create_recipe(reservesys=True)
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe, system=system)
            job.update_status()
        self.assertEquals(recipe.status, TaskStatus.reserved)
        s = requests.Session()
        requests_login(s, user.user_name, 'password')
        response = put_json(get_server_base() +
                'systems/%s/reservations/+current' % system.fqdn,
                session=s, data=dict(finish_time='now'))
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            job.update_status()
            self.assertEquals(job.status, TaskStatus.completed)
            self.assertEquals(system.user, None)
