#!/usr/bin/python
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup
import unittest, time, re, os
from turbogears.database import session, get_engine

class AddSystem(SeleniumTestCase):
    def setUp(self):
        with session.begin():
            data_setup.create_labcontroller(fqdn=u'lab-devel.rhts.eng.bos.redhat.com')
        self.selenium = self.get_selenium()
        self.selenium.start()
        self.condition_report = 'never being fixed'
        logged_in = self.login()

    def test_case_1(self):
        system_details = dict(fqdn = 'test-system-1',
                              lender = 'lender',
                              serial = '44444444444',
                              status = 'Automated', 
                              lab_controller = 'lab-devel.rhts.eng.bos.redhat.com',
                              type = 'Machine',
                              private = False,
                              shared = False,
                              vendor = 'Intel',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        sel = self.selenium
        sel.open("")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='fedora-content']/a")
        sel.wait_for_page_to_load("30000")
        self.add_system(**system_details)
        self.assert_system_view_text('fqdn', system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])
        self.assert_system_view_text('shared', 'False')
        self.assert_system_view_text('private', 'False')
        results = self.check_db(system_details['fqdn'])
        if str(results['status']) != system_details['status']:
            raise AssertionError('System status not set correctly to %s' % system_details['status'])

    def test_case_2(self):
        system_details = dict(fqdn = 'test-system-2',
                              lender = '',
                              serial = '44444444444',
                              status = 'Broken',
                              lab_controller = 'None',
                              type = 'Laptop',
                              private = False,
                              shared = False,
                              vendor = 'Intel',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        sel = self.selenium
        sel.open("")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='fedora-content']/a")
        sel.wait_for_page_to_load("30000")
        self.add_system(**system_details)
        self.assert_system_view_text('fqdn', system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('status_reason', self.condition_report)
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])
        self.assert_system_view_text('shared', 'False')
        self.assert_system_view_text('private', 'False')

    def test_case_3(self):
        system_details = dict(fqdn = 'test-system-3',
                              lender = 'lender',
                              serial = '444gggg4444',
                              status = 'Automated', 
                              lab_controller = 'None',
                              type = 'Resource',
                              private = True,
                              shared = False,
                              vendor = 'AMD',
                              model = 'model',
                              location = '',
                              mac = '33333333')

        sel = self.selenium
        sel.open("")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='fedora-content']/a")
        sel.wait_for_page_to_load("30000")
        self.add_system(**system_details)
        self.assert_system_view_text('fqdn', system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])
        self.assert_system_view_text('shared', 'False')
        self.assert_system_view_text('private', 'True')

    def test_case_4(self):
        system_details = dict(fqdn = 'test-system-4',
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken',
                              lab_controller = 'None',
                              type = 'Prototype',
                              private = True,
                              shared = False,
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        sel = self.selenium
        sel.open("")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='fedora-content']/a")
        sel.wait_for_page_to_load("30000")
        self.add_system(**system_details)
        self.assert_system_view_text('fqdn', system_details['fqdn'])
        self.assert_system_view_text('lender', system_details['lender'])
        self.assert_system_view_text('vendor', system_details['vendor'])
        self.assert_system_view_text('model', system_details['model'])
        self.assert_system_view_text('location', system_details['location'])
        self.assert_system_view_text('shared', 'False')
        self.assert_system_view_text('private', 'True')

    def test_case_5(self):
        with session.begin():
            data_setup.create_system(fqdn=u'preexisting-system')
        system_details = dict(fqdn = 'preexisting-system', #should fail as system is already in db
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken', 
                              lab_controller = 'None',
                              type = 'Prototype',
                              private = True,
                              shared = False,
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        sel = self.selenium
        sel.open("")
        sel.wait_for_page_to_load("30000")
        sel.click("//div[@id='fedora-content']/a")
        sel.wait_for_page_to_load("30000")
        self.add_system(**system_details)
        self.assert_(sel.is_text_present("preexisting-system already exists!"))

    def check_db(self,fqdn):
        conn = get_engine().connect()
        result = conn.execute("SELECT status,l.fqdn, type \
                        FROM system \
                            INNER JOIN lab_controller AS l ON system.lab_controller_id = l.id\
                        WHERE system.fqdn = %s", fqdn).fetchone()
        if not result:
            raise AssertionError('Could not find status,type,lab_controller for  system %s in db' % fqdn)
        return {'status' : result[0], 'lab_controller' : result[1], 'type' : result[2] }


    def add_system(self,fqdn=None,lender=None,serial=None,status=None,
                   lab_controller=None,type=None,private=False,shared=False,
                   vendor=None,model=None,location=None,mac=None): 
        sel = self.selenium
        sel.type("form_fqdn", fqdn)
        sel.type("form_lender", lender)
        sel.select("form_status", "label=%s" % status)
        if private:
            sel.click("form_private")
        if status == 'Broken':
            sel.type("form_status_reason", self.condition_report)
        sel.select("form_lab_controller_id", "label=%s" % lab_controller)
        sel.select("form_type", "label=%s" % type)
        sel.type("form_serial", serial)
        sel.type("form_vendor", vendor)
        sel.type("form_model", model)
        sel.type("form_location", location)
        sel.type("form_mac_address", mac)
        sel.click("link=Save Changes")
        sel.wait_for_page_to_load("30000")


    def tearDown(self):
        self.selenium.stop()

if __name__ == "__main__":
        unittest.main()
