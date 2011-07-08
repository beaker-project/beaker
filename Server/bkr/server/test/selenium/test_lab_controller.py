
from turbogears.database import session
import xmlrpclib
from bkr.server.test import data_setup
from bkr.server.test.selenium import SeleniumTestCase, XmlRpcTestCase

class LabControllerTest(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def edit_lab_controller(self, fqdn):
        sel = self.selenium
        sel.click('//ul[@id="menu"]//a[text()="Lab Controllers"]')
        sel.wait_for_page_to_load('30000')
        sel.click('link=%s' % fqdn)
        sel.wait_for_page_to_load('30000')

    # https://bugzilla.redhat.com/show_bug.cgi?id=717424

    def test_make_primary_mirror(self):
        lab_controller = data_setup.create_labcontroller(fqdn=u'make_me_primary')
        lab_controller.primary_mirror = False
        session.flush()
        self.login()
        self.edit_lab_controller(lab_controller.fqdn)
        sel = self.selenium
        sel.check('primary_mirror')
        sel.submit('form')
        sel.wait_for_page_to_load('30000')
        session.refresh(lab_controller)
        self.assertEqual(lab_controller.primary_mirror, True)

    def test_make_not_primary_mirror(self):
        lab_controller = data_setup.create_labcontroller(fqdn=u'make_me_not_primary')
        lab_controller.primary_mirror = True
        session.flush()
        self.login()
        self.edit_lab_controller(lab_controller.fqdn)
        sel = self.selenium
        sel.uncheck('primary_mirror')
        sel.submit('form')
        sel.wait_for_page_to_load('30000')
        session.refresh(lab_controller)
        self.assertEqual(lab_controller.primary_mirror, False)

class LabControllerXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=717424
    def test_removing_distro_from_primary_mirror_removes_from_all(self):
        primary_lc = data_setup.create_labcontroller(fqdn=u'primary_lc')
        primary_lc.primary_mirror = True
        primary_lc.user.password = u'password'
        other_lc = data_setup.create_labcontroller(fqdn=u'other_lc')
        other_lc.primary_mirror = False
        distro = data_setup.create_distro()
        # distro should be in all lab controllers now
        self.assert_(primary_lc in distro.lab_controllers)
        self.assert_(other_lc in distro.lab_controllers)
        session.flush()

        self.server.auth.login_password(primary_lc.user.user_name, u'password')
        self.server.labcontrollers.removeDistro(distro.install_name)

        session.refresh(distro)
        self.assertEqual(len(distro.lab_controllers), 0)
