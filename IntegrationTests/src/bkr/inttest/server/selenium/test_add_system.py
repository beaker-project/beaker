
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from bkr.server.model import session, System, SystemPermission
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base

class AddSystem(WebDriverTestCase):
    def setUp(self):
        with session.begin():
            data_setup.create_labcontroller(fqdn=u'lab-devel.rhts.eng.bos.redhat.com')
        self.browser = self.get_browser()
        self.condition_report = 'never being fixed'
        login(self.browser)

    # the default values are the same as that presented by the Web UI
    def add_system(self, fqdn='', lender='', serial='', status='Automated',
                   lab_controller='None', type='Laptop',
                   vendor='', model='', location='', mac=''):
        b = self.browser
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_name('lender').send_keys(lender)
        Select(b.find_element_by_name('status')).select_by_visible_text(status)
        if status == 'Broken':
            b.find_element_by_name('status_reason').send_keys(self.condition_report)
        Select(b.find_element_by_name('lab_controller_id'))\
            .select_by_visible_text(lab_controller)
        Select(b.find_element_by_name('type')).select_by_visible_text(type)
        b.find_element_by_name('serial').send_keys(serial)
        b.find_element_by_name('vendor').send_keys(vendor)
        b.find_element_by_name('model').send_keys(model)
        b.find_element_by_name('location').send_keys(location)
        b.find_element_by_name('mac_address').send_keys(mac)
        b.find_element_by_name('form').submit()

    def assert_system_view_text(self, field, val):
        text = self.browser.find_element_by_xpath('//div[@class="controls" and '
                'preceding-sibling::label/@for="form_%s"]/span' % field).text
        self.assertEqual(text.strip(), val)

    def test_case_1(self):
        system_details = dict(fqdn = 'test-system-1',
                              lender = 'lender',
                              serial = '44444444444',
                              status = 'Automated', 
                              lab_controller = 'lab-devel.rhts.eng.bos.redhat.com',
                              type = 'Machine',
                              vendor = 'Intel',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system(**system_details)
        self.assertEquals(b.find_element_by_xpath('//h1').text,
                          system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])
        with session.begin():
            system = System.query.filter_by(fqdn=system_details['fqdn']).one()
            self.assertEquals(unicode(system.status), system_details['status'])

    def test_case_2(self):
        system_details = dict(fqdn = 'test-system-2',
                              lender = '',
                              serial = '44444444444',
                              status = 'Broken',
                              lab_controller = 'None',
                              type = 'Laptop',
                              vendor = 'Intel',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system(**system_details)
        self.assertEquals(b.find_element_by_xpath('//h1').text,
                system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('status_reason', self.condition_report)
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])

    def test_case_3(self):
        system_details = dict(fqdn = 'test-system-3',
                              lender = 'lender',
                              serial = '444gggg4444',
                              status = 'Automated', 
                              lab_controller = 'None',
                              type = 'Resource',
                              vendor = 'AMD',
                              model = 'model',
                              location = '',
                              mac = '33333333')

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system(**system_details)
        self.assertEquals(b.find_element_by_xpath('//h1').text,
                system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])

    def test_case_4(self):
        system_details = dict(fqdn = 'test-system-4',
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken',
                              lab_controller = 'None',
                              type = 'Prototype',
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system(**system_details)
        self.assertEquals(b.find_element_by_xpath('//h1').text,
                system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])

    def test_case_5(self):
        with session.begin():
            data_setup.create_system(fqdn=u'preexisting-system')
        system_details = dict(fqdn = 'preexisting-system', #should fail as system is already in db
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken', 
                              lab_controller = 'None',
                              type = 'Prototype',
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system(**system_details)
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'preexisting-system already exists!')

    #https://bugzilla.redhat.com/show_bug.cgi?id=1021737
    def test_empty_fqdn(self):

        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        self.add_system()
        error_msg = b.find_element_by_css_selector(
            '.control-group.error .help-inline').text
        self.assertEquals(error_msg, 'Please enter a value')

    def test_grants_view_permission_to_everybody_by_default(self):
        fqdn = data_setup.unique_name(u'test-add-system%s.example.invalid')
        b = self.browser
        b.get(get_server_base())
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('fqdn').send_keys(fqdn)
        b.find_element_by_name('form').submit()
        b.find_element_by_xpath('//h1[text()="%s"]' % fqdn)
        with session.begin():
            system = System.query.filter(System.fqdn == fqdn).one()
            self.assertTrue(system.custom_access_policy.grants_everybody(
                    SystemPermission.view))
