import unittest
import datetime
from turbogears.database import session
from bkr.server.model import SSHPubKey, ConfigItem, User
from bkr.inttest import data_setup
from bkr.inttest.server.selenium import SeleniumTestCase


class SystemManualProvisionTest(SeleniumTestCase):

    def setUp(self):
        self.selenium = self.get_selenium()
        self.selenium.start()
        with session.begin():
            self.lab_controller = data_setup.create_labcontroller()
            self.user = data_setup.create_user(password=u'password')
            self.distro_tree = data_setup.create_distro_tree(osmajor=u'Fedora',
                    arch=u'i386')
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

if __name__ == "__main__":
    unittest.main()
