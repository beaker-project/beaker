import unittest
import datetime
from turbogears.database import session
from bkr.server.model import SSHPubKey, ConfigItem, User, Provision
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import SeleniumTestCase, WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from selenium.webdriver.support.ui import Select
from bkr.inttest.assertions import wait_for_condition

class SystemManualProvisionTest(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.user = data_setup.create_user(password=u'password')
            self.distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora',
                    arch=u'i386', lab_controllers=[self.lab_controller])
            self.system = data_setup.create_system(arch=u'i386',
                    owner=self.user, status=u'Manual', shared=True)
            self.system.lab_controller = self.lab_controller
            self.system.user = self.user
        self.login(user=self.user.user_name,password='password')

    def test_manual_provision_with_ssh_keys(self):
        sel = self.selenium
        system = self.system
        with session.begin():
            user = system.user
            user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'AAAAvalidkeyyeah', u'user@host'))
        sel.open("")
        sel.type("simplesearch", "%s" % system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click("link=Provision")
        sel.select("provision_prov_install", "index=0")
        sel.click("//a[@href='javascript:document.provision.submit();']")
        sel.wait_for_page_to_load("30000")
        self.assert_("Successfully Provisioned %s" % system.fqdn in sel.get_text('css=.flash'))

    def test_provision_rejected_with_expired_root_password(self):
        sel = self.selenium
        system = self.system
        user = system.user
        user.root_password = "MothersMaidenName"
        user.rootpw_changed = datetime.datetime.utcnow() - datetime.timedelta(days=35)
        ConfigItem.by_name('root_password_validity').set(30,
                user=User.by_user_name(data_setup.ADMIN_USER))
        session.flush()
        sel.open("")
        sel.type("simplesearch", "%s" % system.fqdn)
        sel.click("search")
        sel.wait_for_page_to_load("30000")
        sel.click("link=%s" % system.fqdn)
        sel.wait_for_page_to_load("30000")
        sel.click("link=Provision")
        sel.select("provision_prov_install", "index=0")
        sel.click("//a[@href='javascript:document.provision.submit();']")
        sel.wait_for_page_to_load("30000")
        self.assert_("root password has expired" in sel.get_text('css=.flash'))

class SystemManualProvisionInstallOptionsTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.user = data_setup.create_user(password=u'password')
            self.system = data_setup.create_system(lab_controller=self.lab_controller, \
                                                       owner=self.user,status=u'Manual', shared=True)
            self.system.user = self.user
            self.distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora', arch=u'i386',
                    lab_controllers=[self.lab_controller])
            self.system.provisions[self.distro_tree.arch] = \
                Provision(arch=self.distro_tree.arch,
                          kernel_options=u'key1=value1 key1=value2 key1 key2=value key3')
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    #https://bugzilla.redhat.com/show_bug.cgi?id=886875
    def test_kernel_install_options_propagated_provision(self):

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)

        # provision tab
        b.find_element_by_link_text('Provision').click()

        # select the distro
        Select(b.find_element_by_name('prov_install'))\
            .select_by_visible_text(unicode(self.distro_tree))

        def provision_koptions_populated():
            if b.find_element_by_xpath("//input[@id='provision_koptions']").\
                    get_attribute('value') == \
                    u'key1=value1 key1=value2 key2=value key3 noverifyssl':
                return True

        wait_for_condition(provision_koptions_populated)

        # provision
        b.find_element_by_xpath("//form[@name='provision']//a[text()='Provision']").click()
        self.assert_(b.find_element_by_class_name('flash').text.startswith('Success'))

        # check
        self.assertEquals(self.system.command_queue[1].action, u'configure_netboot')
        self.assert_(u'key1=value1 key1=value2 key2=value key3' in \
                         self.system.command_queue[1].kernel_options)

if __name__ == "__main__":
    unittest.main()
