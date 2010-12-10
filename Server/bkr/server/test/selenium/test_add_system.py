#!/usr/bin/python
import bkr.server.test.selenium
from bkr.server.test import data_setup
import unittest, time, re, os
from turbogears.database import session, get_engine

class AddSystem(bkr.server.test.selenium.SeleniumTestCase):
    def setUp(self):
        data_setup.create_labcontroller(fqdn=u'lab-devel.rhts.eng.bos.redhat.com')
        session.flush()

        try:
            self.verificationErrors = []
            self.selenium = self.get_selenium()
            self.selenium.start()
            self.condition_report = 'never being fixed'
            logged_in = self.login() 
            if not logged_in:
                raise AssertionError('Could not log in')
        except AssertionError, e: self.verificationErrors.append(str(e))    
        except Exception,e:self.verificationErrors.append(str(e))    


    def test_case_1(self):
        system_details = dict(fqdn = 'test_system_1',
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

        #system_details = [fqdn,lender,serial,status,lab_controller,
        #                  type,private,shared,vendor,model,location,mac]
        try:
            sel = self.selenium
            sel.open("")
            sel.wait_for_page_to_load("3000")
            sel.click("//div[@id='fedora-content']/a")
            sel.wait_for_page_to_load("3000")
            self.add_system(**system_details)
            self.failUnless(sel.is_text_present("DetailsArch(s)Key/ValuesGroupsExcluded FamiliesPowerNotesInstall OptionsProvisionLab InfoHistoryTasks")) 
            self.assertEqual(system_details['fqdn'], sel.get_value("form_fqdn"))
            self.assertEqual(system_details['lender'], sel.get_value("form_lender")) 
            self.assertEqual(system_details['vendor'], sel.get_value("form_vendor"))
            self.assertEqual(system_details['model'], sel.get_value("form_model"))
            self.assertEqual(system_details['location'], sel.get_value("form_location"))
            self.assertEqual("off", sel.get_value("form_shared"))
            self.assertEqual("off", sel.get_value("form_private"))
            results = self.check_db(system_details['fqdn'])
            if str(results['status']) != system_details['status']:
                raise AssertionError('System status not set correctly to %s' % system_details['status'])
        except AssertionError,e:self.verificationErrors.append(str(e))    
        except Exception,e:self.verificationErrors.append(str(e))    

    def test_case_2(self):
        system_details = dict(fqdn = 'test_system_2',
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

        #system_details = [fqdn,lender,serial,status,lab_controller,
        #                  type,private,shared,vendor,model,location,mac]
        try:
            sel = self.selenium
            sel.open("")
            sel.wait_for_page_to_load("3000")
            sel.click("//div[@id='fedora-content']/a")
            sel.wait_for_page_to_load("3000")
            self.add_system(**system_details)
            self.failUnless(sel.is_text_present("DetailsArch(s)Key/ValuesGroupsExcluded FamiliesPowerNotesInstall OptionsProvisionLab InfoHistoryTasks")) 
            self.assertEqual(system_details['fqdn'], sel.get_value("form_fqdn"))
            self.assertEqual(system_details['lender'], sel.get_value("form_lender"))
            self.assertEqual(self.condition_report, sel.get_value("form_status_reason"))
            self.assertEqual(system_details['vendor'], sel.get_value("form_vendor"))
            self.assertEqual(system_details['model'], sel.get_value("form_model"))
            self.assertEqual(system_details['location'], sel.get_value("form_location"))
            self.assertEqual("off", sel.get_value("form_shared"))
            self.assertEqual("off", sel.get_value("form_private"))
        except Exception,e:self.verificationErrors.append(str(e))

    def test_case_3(self):
        system_details = dict(fqdn = 'test_system_3',
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

        #system_details = [fqdn,lender,serial,status,lab_controller,
        #                  type,private,shared,vendor,model,location,mac]
        try:
            sel = self.selenium 
            sel.open("")
            sel.wait_for_page_to_load("3000")
            sel.click("//div[@id='fedora-content']/a")
            sel.wait_for_page_to_load("3000")
            self.add_system(**system_details)
            self.failUnless(sel.is_text_present("DetailsArch(s)Key/ValuesGroupsExcluded FamiliesPowerNotesInstall OptionsProvisionLab InfoHistoryTasks")) 
            self.assertEqual(system_details['fqdn'], sel.get_value("form_fqdn"))
            self.assertEqual(system_details['lender'], sel.get_value("form_lender")) 
            self.assertEqual(system_details['vendor'], sel.get_value("form_vendor"))
            self.assertEqual(system_details['model'], sel.get_value("form_model"))
            self.assertEqual(system_details['location'], sel.get_value("form_location"))
            self.assertEqual("off", sel.get_value("form_shared"))
            self.assertEqual("on", sel.get_value("form_private")) 
        except Exception,e:self.verificationErrors.append(str(e))    

    def test_case_4(self):
        system_details = dict(fqdn = 'test_system_4',
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken',
                              lab_controller = 'None',
                              type = 'Virtual',
                              private = True,
                              shared = False,
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        #system_details = [fqdn,lender,serial,status,lab_controller,
        #                  type,private,shared,vendor,model,location,mac]
        try:
            sel = self.selenium 
            sel.open("")
            sel.wait_for_page_to_load("3000")
            sel.click("//div[@id='fedora-content']/a")
            sel.wait_for_page_to_load("3000")
            self.add_system(**system_details)
            self.failUnless(sel.is_text_present("DetailsArch(s)Key/ValuesGroupsExcluded FamiliesNotesInstall OptionsLab InfoHistoryTasks"))
            self.assertEqual(system_details['fqdn'], sel.get_value("form_fqdn"))
            self.assertEqual(system_details['lender'], sel.get_value("form_lender"))
            self.assertEqual(self.condition_report, sel.get_value("form_status_reason"))
            self.assertEqual(system_details['vendor'], sel.get_value("form_vendor"))
            self.assertEqual(system_details['model'], sel.get_value("form_model"))
            self.assertEqual(system_details['location'], sel.get_value("form_location"))
            self.assertEqual("off", sel.get_value("form_shared"))
            self.assertEqual("on", sel.get_value("form_private"))
        except Exception,e:self.verificationErrors.append(str(e))    

    def test_case_5(self):
        data_setup.create_system(fqdn=u'preexisting-system')
        session.flush()
        system_details = dict(fqdn = 'preexisting-system', #should fail as system is already in db
                              lender = 'lender',
                              serial = '444g!!!444',
                              status = 'Broken', 
                              lab_controller = 'None',
                              type = 'Virtual',
                              private = True,
                              shared = False,
                              vendor = 'AMD',
                              model = 'model',
                              location = 'brisbane',
                              mac = '33333333')

        #system_details = [fqdn,lender,serial,status,lab_controller,
        #                  type,private,shared,vendor,model,location,mac]
        try:
            sel = self.selenium 
            sel.open("")
            sel.wait_for_page_to_load("3000")
            sel.click("//div[@id='fedora-content']/a")
            sel.wait_for_page_to_load("3000")
            self.add_system(**system_details)
            self.assert_(sel.is_text_present("preexisting-system already exists!"))
        except Exception,e:self.verificationErrors.append(str(e))

    def check_db(self,fqdn):
        conn = get_engine().connect()
        result = conn.execute("SELECT s.status,l.fqdn, t.type \
                        FROM system \
                            INNER JOIN system_status AS s ON s.id = system.status_id\
                            INNER JOIN system_type AS t ON t.id = system.type_id\
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
        sel.select("form_status_id", "label=%s" % status)
        if private:
            sel.click("form_private")
        if status == 'Broken':
            sel.type("form_status_reason", self.condition_report)
        sel.select("form_lab_controller_id", "label=%s" % lab_controller)
        sel.select("form_type_id", "label=%s" % type)
        sel.type("form_serial", serial)
        sel.type("form_vendor", vendor)
        sel.type("form_model", model)
        sel.type("form_location", location)
        sel.type("form_mac_address", mac)
        sel.click("link=Save Changes")
        sel.wait_for_page_to_load("3000")


    def tearDown(self):
        self.selenium.stop()
        self.assertEqual([], self.verificationErrors)
      

if __name__ == "__main__":
        unittest.main()
