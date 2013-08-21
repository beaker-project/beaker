
import xmlrpclib
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase, XmlRpcTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import Permission, User

def go_to_distro_view(sel, distro):
    sel.open('distros/view?id=%s' % distro.id)

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
        sel.click('//a[text()="Add ( + )"]')
        sel.wait_for_page_to_load('30000')
        self.assertEquals(sel.get_text('css=.flash'), 'Added Tag HAPPY')
        self.assert_(sel.is_element_present(
                '//td[normalize-space(text())="HAPPY"]'))

    def test_can_remove_tag_from_distro(self):
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        sel.click( # delete link inside cell beside "SAD" cell
                '//table[@class="list"]//td'
                '[normalize-space(preceding-sibling::td[1]/text())="SAD"]'
                '//a[text()="Delete ( - )"]')
        self.wait_and_try(lambda: self.failUnless(sel.is_text_present("Are you sure")))
        sel.click("//button[@type='button' and .//text()='Yes']")
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
                '//a[text()="Delete ( - )"]')

        self.wait_and_try(lambda: self.failUnless(sel.is_text_present("Are you sure")))
        sel.click("//button[@type='button' and .//text()='Yes']")
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=830940
    def test_provision_links_arent_shown_for_expired_trees(self):
        with session.begin():
            not_expired_tree = data_setup.create_distro_tree(
                    distro=self.distro, variant=u'Client')
            expired_tree = data_setup.create_distro_tree(
                    distro=self.distro, variant=u'Server')
            session.flush()
            expired_tree.lab_controller_assocs[:] = []
        self.login(data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        sel = self.selenium
        go_to_distro_view(sel, self.distro)
        self.assertEquals(
                sel.get_text('//table[@class="list"]/tbody/tr[td[1]/a/text()="%s"]/td[4]'
                % not_expired_tree.id),
                'Pick System Pick Any System')
        self.assertEquals(
                sel.get_text('//table[@class="list"]/tbody/tr[td[1]/a/text()="%s"]/td[4]'
                % expired_tree.id),
                '')


class DistroExpireXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.lc = data_setup.create_labcontroller()
        self.distro = data_setup.create_distro()
        self.distro_tree = data_setup.create_distro_tree(distro=self.distro,
            arch='x86_64', lab_controllers=[self.lc])
        self.server = self.get_server()
        user = User.by_user_name(data_setup.ADMIN_USER)
        user.groups[0].permissions[:] = user.groups[0].permissions + [ Permission.by_name('distro_expire')]

    def test_activity_created_with_expire(self):
        self.server.auth.login_password(data_setup.ADMIN_USER,
            data_setup.ADMIN_PASSWORD)
        self.server.distros.expire(self.distro.name, 'CUSTOMSERVICE')
        session.expire_all()
        with session.begin():
            activity = self.distro_tree.activity[0]
            self.assertEquals(activity.service, u'CUSTOMSERVICE')


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
