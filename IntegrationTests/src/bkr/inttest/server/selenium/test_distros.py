
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import xmlrpclib
import requests
from turbogears.database import session
from bkr.inttest.server.selenium import WebDriverTestCase, XmlRpcTestCase
from bkr.inttest.server.webdriver_utils import login, delete_and_confirm
from bkr.inttest import data_setup, with_transaction, get_server_base
from bkr.server.model import Permission, User

def go_to_distro_view(browser, distro):
    browser.get(get_server_base() + 'distros/view?id=%s' % distro.id)

class DistroViewTest(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        self.distro.tags.append(u'SAD')
        self.user = data_setup.create_user(password=u'distro')
        self.browser = self.get_browser()

    def test_can_add_tag_to_distro(self):
        b = self.browser
        login(b, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        go_to_distro_view(b, self.distro)
        b.find_element_by_id('tags_tag_text').send_keys('HAPPY')
        b.find_element_by_link_text('Add').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Added Tag HAPPY')
        b.find_element_by_xpath(
                '//td[normalize-space(text())="HAPPY"]')
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Added')
            self.assertEquals(activity.old_value, None)
            self.assertEquals(activity.new_value, u'HAPPY')

    def test_can_remove_tag_from_distro(self):
        b = self.browser
        login(b, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        go_to_distro_view(b, self.distro)
        delete_and_confirm(b, '//td[normalize-space(preceding-sibling::td[1]/text())="SAD"]')
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Removed Tag SAD')
        b.find_element_by_xpath('//div[@class="tags"]//table[not('
                './/td[normalize-space(text())="SAD"])]')
        with session.begin():
            session.refresh(self.distro)
            self.assert_(u'SAD' not in self.distro.tags)
        with session.begin():
            session.refresh(self.distro)
            activity = self.distro.activity[0]
            self.assertEquals(activity.field_name, u'Tag')
            self.assertEquals(activity.service, u'WEBUI')
            self.assertEquals(activity.action, u'Removed')
            self.assertEquals(activity.old_value, u'SAD')
            self.assertEquals(activity.new_value, None)

    def test_non_admin_user_cannot_add_tag(self):
        b = self.browser
        login(b, self.user.user_name, 'distro')
        go_to_distro_view(b, self.distro)
        b.find_element_by_xpath('//div[@class="tags" and not(.//a)]')

        response = requests.get(get_server_base() +
                'distros/save_tag?id=%s&tag.text=HAPPY' % self.distro.id)
        self.assertEquals(response.status_code, 403)

    def test_non_admin_user_cannot_remove_tag(self):
        b = self.browser
        login(b, self.user.user_name, 'distro')
        go_to_distro_view(b, self.distro)
        b.find_element_by_xpath('//div[@class="tags" and not(.//a)]')

        response = requests.get(get_server_base() +
                'distros/tag_remove?id=%s&tag=SAD' % self.distro.id)
        self.assertEquals(response.status_code, 403)

    # https://bugzilla.redhat.com/show_bug.cgi?id=830940
    def test_provision_links_arent_shown_for_expired_trees(self):
        with session.begin():
            not_expired_tree = data_setup.create_distro_tree(
                    distro=self.distro, variant=u'Client')
            expired_tree = data_setup.create_distro_tree(
                    distro=self.distro, variant=u'Server')
            session.flush()
            expired_tree.lab_controller_assocs[:] = []
        b = self.browser
        login(b, data_setup.ADMIN_USER, data_setup.ADMIN_PASSWORD)
        go_to_distro_view(b, self.distro)
        self.assertEquals(b.find_element_by_xpath(
                '//table//tr[td[1]/a/text()="%s"]/td[4]'
                % not_expired_tree.id).text,
                'Provision')
        self.assertEquals(b.find_element_by_xpath(
                '//table//tr[td[1]/a/text()="%s"]/td[4]'
                % expired_tree.id).text,
                '')


class DistroExpireXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.group = data_setup.create_group()
        # grant the group distro_expire permission
        self.group.permissions.append(Permission.by_name(u'distro_expire'))
        self.user = data_setup.create_user(password=u'password')
        self.group.add_member(self.user)
        self.lc = data_setup.create_labcontroller(user=self.user)
        self.distro = data_setup.create_distro()
        self.distro_tree = data_setup.create_distro_tree(distro=self.distro,
            arch='x86_64', lab_controllers=[self.lc])
        self.server = self.get_server()


    def test_activity_created_with_expire(self):
        self.server.auth.login_password(self.user.user_name, u'password')
        self.server.distros.expire(self.distro.name, u'CUSTOMSERVICE')
        session.expire_all()
        with session.begin():
            activity = self.distro_tree.activity[0]
            self.assertEquals(activity.service, u'CUSTOMSERVICE')


class DistroEditVersionXmlRpcTest(XmlRpcTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1173368
    def test_empty_version(self):
        self.server.auth.login_password(data_setup.ADMIN_USER,
                                        data_setup.ADMIN_PASSWORD)
        try:
            self.server.distros.edit_version(self.distro.name, '')
            self.fail('should raise')
        except xmlrpclib.Fault, e:
             self.assertIn('OSMajor cannot be empty', e.faultString)


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
