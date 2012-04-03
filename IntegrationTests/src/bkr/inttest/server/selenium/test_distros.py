
from nose.plugins.skip import SkipTest
import xmlrpclib
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.inttest import data_setup, stub_cobbler, with_transaction

def go_to_distro_view(sel, distro):
    sel.open('distros/view?id=%s' % distro.id)

class DistroRescanTest(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        raise SkipTest('Cobbler removal')
        self.stub_cobbler_thread = stub_cobbler.StubCobblerThread()
        self.stub_cobbler_thread.start()
        self.lab_controller = data_setup.create_labcontroller(
                fqdn=u'localhost:%d' % self.stub_cobbler_thread.port)
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()
        self.stub_cobbler_thread.stop()

    def test_rescan(self):
        # Create the distros
        with session.begin():
            distro1 = data_setup.create_distro(name=u'pivot')
            dh_1 = self.stub_cobbler_thread.cobbler.get_distro_handle(distro1.install_name, 'logged_in')
            distro2 = data_setup.create_distro(name=u'fisher')
            dh_2 = self.stub_cobbler_thread.cobbler.get_distro_handle(distro2.install_name, 'logged_in')
            distro3 = data_setup.create_distro(name=u'twentyniner')
            dh_3 = self.stub_cobbler_thread.cobbler.get_distro_handle(distro3.install_name, 'logged_in')

        # login
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium

        # Verify they have our lab controller
        go_to_distro_view(sel, distro1)
        self.failUnless(sel.is_text_present(self.lab_controller.fqdn))
        go_to_distro_view(sel, distro2)
        self.failUnless(sel.is_text_present(self.lab_controller.fqdn))
        go_to_distro_view(sel, distro3)
        self.failUnless(sel.is_text_present(self.lab_controller.fqdn))

        # Remove one of the distros from our lab controller
        self.stub_cobbler_thread.cobbler.remove_distro(dh_2, 'logged_in')

        # re-scan
        sel.open("labcontrollers/")
        sel.wait_for_page_to_load('30000')
        sel.click("//a[@href='rescan?id=%s']" % self.lab_controller.id)
        sel.wait_for_page_to_load('30000')

        # Verify that we still have the distros we should and the removed
        # one has been removed.
        go_to_distro_view(sel, distro1)
        self.failUnless(sel.is_text_present(self.lab_controller.fqdn))
        go_to_distro_view(sel, distro2)
        self.failUnless(not sel.is_text_present(self.lab_controller.fqdn))
        go_to_distro_view(sel, distro3)
        self.failUnless(sel.is_text_present(self.lab_controller.fqdn))


class DistroViewTest(SeleniumTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        self.distro.tags.append(u'SAD')
        self.user = data_setup.create_user(password=u'distro')
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_can_add_tag_to_distro(self):
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        sel.type('tags_tag_text', 'HAPPY')
        sel.click('//form[@name="tags"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Added Tag HAPPY')
        self.assert_(sel.is_element_present(
                '//form[@name="tags"]//td[normalize-space(text())="HAPPY"]'))

    def test_can_remove_tag_from_distro(self):
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        sel.click( # delete link inside cell beside "SAD" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="SAD"]'
                '/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Removed Tag SAD')
        self.assert_(not sel.is_element_present(
                '//form[@name="tags"]//td[normalize-space(text())="SAD"]'))
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'SAD' not in self.distro.tags)

    def test_non_admin_user_cannot_add_tag(self):
        self.login(self.user.user_name, 'distro')
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        self.assert_(not sel.is_element_present(
               '//form[@name="tags"]//a[text()="Add ( + )"]'))
        try:
            sel.open('distros/save_tag?id=%s&tag.text=HAPPY' % self.distro.id,
                    ignoreResponseCode=False)
            self.fail('should raise 403')
        except Exception, e:
            self.assert_('Response_Code = 403' in e.args[0])

    def test_non_admin_user_cannot_remove_tag(self):
        self.login(self.user.user_name, 'distro')
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        self.assert_(not sel.is_element_present(
               '//form[@name="tags"]//a[text()="Delete ( - )"]'))
        try:
            sel.open('distros/tag_remove?id=%s&tag=SAD' % self.distro.id,
                    ignoreResponseCode=False)
            self.fail('should raise 403')
        except Exception, e:
            self.assert_('Response_Code = 403' in e.args[0])

    def test_adding_tag_is_recorded_in_distro_activity(self):
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        sel.type('tags_tag_text', 'HAPPY')
        sel.click('//form[@name="tags"]//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Added Tag HAPPY')
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Added')
            self.assertEquals(activity.old_value, None)
            self.assertEquals(activity.new_value, u'HAPPY')

    def test_removing_tag_is_recorded_in_distro_activity(self):
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        sel.click( # delete link inside cell beside "SAD" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="SAD"]'
                '/a[text()="Delete ( - )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Removed Tag SAD')
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Removed')
            self.assertEquals(activity.old_value, u'SAD')
            self.assertEquals(activity.new_value, None)

class DistroTaggingXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        self.distro.tags.append(u'SAD')
        self.user = data_setup.create_user(password=u'distro')
        self.server = self.get_server()

    def test_can_add_tag_to_distro(self):
        self.server.auth.login_password(
                data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.server.distros.tag(self.distro.name, 'HAPPY')
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'HAPPY' in self.distro.tags)

    def test_can_remove_tag_from_distro(self):
        self.server.auth.login_password(
                data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.server.distros.untag(self.distro.name, 'SAD')
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'SAD' not in self.distro.tags)

    def test_non_admin_user_cannot_add_tag(self):
        self.server.auth.login_password(self.user.user_name, 'distro')
        try:
            self.server.distros.tag(self.distro.name, 'HAPPY')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('IdentityFailure' in e.faultString)

    def test_non_admin_user_cannot_remove_tag(self):
        self.server.auth.login_password(self.user.user_name, 'distro')
        try:
            self.server.distros.untag(self.distro.name, 'SAD')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
            self.assert_('IdentityFailure' in e.faultString)

    def test_adding_tag_is_recorded_in_distro_activity(self):
        self.server.auth.login_password(
                data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.server.distros.tag(self.distro.name, 'HAPPY')
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'XMLRPC')
            self.assertEquals(activity.action, u'Added')
            self.assertEquals(activity.old_value, None)
            self.assertEquals(activity.new_value, u'HAPPY')

    def test_removing_tag_is_recorded_in_distro_activity(self):
        self.server.auth.login_password(
                data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        self.server.distros.untag(self.distro.name, 'SAD')
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'XMLRPC')
            self.assertEquals(activity.action, u'Removed')
            self.assertEquals(activity.old_value, u'SAD')
            self.assertEquals(activity.new_value, None)
