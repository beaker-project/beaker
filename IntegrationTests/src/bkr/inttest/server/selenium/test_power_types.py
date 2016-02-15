
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from sqlalchemy.orm.exc import NoResultFound

from bkr.server.model import session, PowerType, Activity
from bkr.server.tests.data_setup import unique_name
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.requests_utils import login, post_json
from bkr.inttest.server.webdriver_utils import login as browser_login
from bkr.inttest import DatabaseTestCase


class TestPowerTypeEdit(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        browser_login(self.browser)

    def test_creates_powertype_successfully(self):
        b = self.browser
        b.get(get_server_base() + 'powertypes/')

        expected = 'newtype'
        b.find_element_by_css_selector('form input[name=power_type_name]').send_keys(expected)
        b.find_element_by_name('btn_add_power_type').click()

        b.find_element_by_xpath('//li[contains(., "%s")]' % expected)
        with session.begin():
            self.assertTrue(session.query(PowerType).filter_by(name=expected).count())

    def test_does_not_create_duplicated_power_type(self):
        b = self.browser
        b.get(get_server_base() + 'powertypes/')

        powertype = PowerType.query.first()
        self.assertTrue(powertype.name)
        form = b.find_element_by_class_name('add-power-type')
        form.find_element_by_name('power_type_name').send_keys(powertype.name)
        form.submit()
        form.find_element_by_xpath('.//button[normalize-space(string(.))="Add"]')

        with session.begin():
            PowerType.query.filter_by(name=powertype.name).one()

    def test_deletes_power_type_successfully(self):
        powertype_name = unique_name('beerpowered%s')
        with session.begin():
            pt = PowerType(name=powertype_name)
            session.add(pt)
            activity_count = Activity.query.count()

        b = self.browser
        b.get(get_server_base() + 'powertypes/')
        b.find_element_by_xpath('//li[contains(., "%s")]/button' % pt.name).click()
        b.find_element_by_xpath('//ul[contains(@class, "power-types-list") and '
                'not(./li[contains(., "%s")])]' % pt.name)

        with session.begin():
            session.expire_all()
            self.assertEqual(0, session.query(PowerType).filter_by(name=powertype_name).count())
            self.assertEqual(activity_count + 1, Activity.query.count())

    def test_errors_when_deleting_referenced_power_type(self):
        with session.begin():
            system = data_setup.create_system(with_power=False)
            data_setup.configure_system_power(system, power_type=u'ilo')
            power_type_count = PowerType.query.count()

        b = self.browser
        b.get(get_server_base() + 'powertypes/')
        b.find_element_by_xpath('//li[contains(., "ilo")]/button').click()

        b.find_element_by_xpath('//div[contains(@class, "alert-error") and '
                'h4/text()="Error deleting power type" and '
                'contains(string(.), "Power type ilo still referenced")]')
        with session.begin():
            self.assertEqual(power_type_count, PowerType.query.count())


class TestPowerTypesGrid(WebDriverTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1215034
    def test_anonymous_cant_see_form_elements(self):
        b = self.get_browser()
        b.get(get_server_base() + 'powertypes/')
        b.find_element_by_css_selector('ul.power-types-list')
        b.find_element_by_xpath('//body[not(.//form) and not(.//button)]')


class PowerTypeEditHTTPTest(DatabaseTestCase):

    def setUp(self):
        self.powertype_name = unique_name('beerpowered%s')
        with session.begin():
            self.powertype = PowerType(name=self.powertype_name)
            session.add(self.powertype)

        self.s = requests.Session()
        login(self.s)

    def test_successfully_deleted(self):

        response = self.s.delete(get_server_base() + 'powertypes/%s' % self.powertype.id)
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            with self.assertRaises(NoResultFound):
                PowerType.by_name(self.powertype_name)

    def test_error_when_deleting_referenced_power_type(self):
        with session.begin():
            system = data_setup.create_system()
            power_type = system.power.power_type

        response = self.s.delete(get_server_base() + 'powertypes/%s' % power_type.id)
        self.assertEqual(400, response.status_code)
        with session.begin():
            session.expire_all()
            self.assertTrue(session.query(PowerType).filter_by(
                name=power_type.name).count())

    def test_list_powertypes(self):
        with session.begin():
            powertype_names = [x[0] for x in session.query(PowerType.name).all()]

        response = self.s.get(
            get_server_base() + 'powertypes',
            headers={'Accept': 'application/json'},
        )
        response.raise_for_status()

        actual_names = [x['name'] for x in response.json()['power_types']]
        self.assertItemsEqual(powertype_names, actual_names)


class PowerTypeCreationHTTPTest(DatabaseTestCase):

    def setUp(self):
        self.admin_password = '_'
        with session.begin():
            self.admin_user = data_setup.create_admin(password=self.admin_password)
        self.s = requests.Session()

    def test_create_powertype_fails_with_duplicate(self):
        """Fail with an error if a duplicate exist when creating a new power
        type"""
        login(self.s, self.admin_user, self.admin_password)
        expected_name = 'beerpower'

        # create the same power type two times, second time should fail
        post_json(get_server_base() + 'powertypes/',
                  session=self.s,
                  data=dict(name=expected_name))
        response = post_json(get_server_base() + 'powertypes/',
                             session=self.s,
                             data=dict(name=expected_name))
        self.assertEqual(409, response.status_code)

    def test_create_new_powertype_successfully(self):
        with session.begin():
            activity_count = Activity.query.count()

        login(self.s, self.admin_user, self.admin_password)
        expected_name = 'beerpower'
        response = post_json(get_server_base() + 'powertypes/',
                             session=self.s,
                             data=dict(name=expected_name))
        self.assertEqual(201, response.status_code)
        self.assertEqual(expected_name, response.json()['name'])
        with session.begin():
            powertype = PowerType.by_name(expected_name)
            self.assertEqual(expected_name, powertype.name)

            self.assertEqual(activity_count + 1, Activity.query.count())

    def test_nonadmins_cannot_create_powertypes(self):
        """Users missing admin privileges should not be allowed to create
        powertypes."""
        user_password = '_'
        with session.begin():
            user = data_setup.create_user(password=user_password)
            powertypes_amount = session.query(PowerType).count()
        login(self.s, user, user_password)

        response = post_json(get_server_base() + 'powertypes/',
                             session=self.s,
                             data=dict(name='ignored'))
        self.assertEqual(403, response.status_code)
        with session.begin():
            self.assertEqual(powertypes_amount, session.query(PowerType).count())
