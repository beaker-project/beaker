
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_activity_row_present, \
    delete_and_confirm
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import User, DistroActivity, SystemActivity, \
    GroupActivity, DistroTreeActivity

class ActivityTestWD(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
        self.distro_tree1 = data_setup.create_distro_tree(distro=self.distro,
            arch='x86_64')
        self.distro_tree2 = data_setup.create_distro_tree(distro=self.distro,
            arch='i386')

        self.distro_tree1.activity.append(DistroTreeActivity(
            user=User.by_user_name(data_setup.ADMIN_USER),
            service=u'testdata', field_name=u'Nonesente',
            old_value=u'sdfas', new_value=u'sdfa', action='Added'))
        self.distro_tree2.activity.append(DistroTreeActivity(
            user=User.by_user_name(data_setup.ADMIN_USER), 
            service=u'testdata', field_name=u'Noneseonce',
            old_value=u'bsdf', new_value=u'sdfas', action='Added'))

        self.distro.activity.append(DistroActivity(
                user=User.by_user_name(data_setup.ADMIN_USER), service=u'testdata',
                action=u'Nothing', field_name=u'Nonsense',
                old_value=u'asdf', new_value=u'omgwtfbbq'))
        self.system = data_setup.create_system()
        self.system.activity.append(SystemActivity(
                user=User.by_user_name(data_setup.ADMIN_USER), service=u'testdata',
                action=u'Nothing', field_name=u'Nonsense',
                old_value=u'asdf', new_value=u'omgwtfbbq'))
        self.group2 = data_setup.create_group()
        self.group = data_setup.create_group()
        self.group.activity.append(GroupActivity(
                user=User.by_user_name(data_setup.ADMIN_USER), service=u'testdata',
                action=u'Nothing', field_name=u'Nonsense',
                old_value=u'asdf', new_value=u'omgwtfbbq'))
        self.browser = self.get_browser()

    def test_can_search_custom_service(self):
        with session.begin():
            self.distro_tree1.activity.append(DistroTreeActivity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE', field_name=u'Nonesente',
                old_value=u'sdfas', new_value=u'sdfa', action='Removed'))
            self.distro_tree2.activity.append(DistroTreeActivity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE2', field_name=u'Noneseonce',
                old_value=u'bsdf', new_value=u'sdfas', action='Removed'))
        b = self.browser
        b.get(get_server_base() + 'activity/distrotree')
        b.find_element_by_link_text('Show Search Options').click()
        # Make sure only distrotree1 is returned
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='Via']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys('TESTSERVICE')
        b.find_element_by_id('searchform').submit()
        self.assertTrue(is_activity_row_present(b, via='TESTSERVICE', action='Removed',
            object_='DistroTree: %s' % self.distro_tree1))
        self.assertFalse(is_activity_row_present(b, via='TESTSERVICE2', action='Removed',
            object_='DistroTree: %s' % self.distro_tree2))

    def test_can_search_by_distro_tree_specifics(self):
        b = self.browser
        b.get(get_server_base() + 'activity/distrotree')
        b.find_element_by_link_text('Show Search Options').click()
        # Make sure only distrotree1 is returned
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='DistroTree/Arch']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.distro_tree1.arch.arch)

        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath("//select[@id='activitysearch_1_table']/option[@value='DistroTree/Variant']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_1_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_1_value']").send_keys(self.distro_tree1.variant)

        b.find_element_by_link_text('Add').click()
        b.find_element_by_xpath("//select[@id='activitysearch_2_table']/option[@value='DistroTree/Distro Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_2_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_2_value']").send_keys(self.distro_tree1.distro.name)

        b.find_element_by_id('searchform').submit()

        self.assert_(is_activity_row_present(b,
                object_='DistroTree: %s' % self.distro_tree1))

        self.assert_(not is_activity_row_present(b,
                object_='DistroTree: %s' % self.distro_tree2))

    def test_can_search_by_system_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='System/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.system.fqdn)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,
                object_='System: %s' % self.system.fqdn))

    def test_can_search_by_distro_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/distro')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath('//select[@id="activitysearch_0_table"]/option[@value="Distro/Name"]').click()
        b.find_element_by_xpath('//select[@id="activitysearch_0_operation"]/option[@value="is"]').click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.distro.name)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,
                object_='Distro: %s' % self.distro.name))

    def test_can_search_by_group_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/group')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='Group/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.group.display_name)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,
                object_='Group: %s' % self.group.display_name))

    def test_group_removal_is_noticed(self):
        self.group.systems.append(self.system)
        session.flush()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/')
        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b.find_element_by_id('Search').submit()
        delete_and_confirm(b, "//tr[td/a[normalize-space(text())='%s']]" % self.group.group_name,
            'Remove')
        should_have_deleted_msg = b.find_element_by_xpath('//body').text
        self.assert_('%s deleted' % self.group.display_name in should_have_deleted_msg)

        # Check it's recorded in System Activity
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Show Search Options').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='Action']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys('Removed')
        b.find_element_by_link_text('Add').click()

        b.find_element_by_xpath("//select[@id='activitysearch_1_table']/option[@value='Old Value']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_1_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_1_value']").send_keys(self.group.display_name)
        b.find_element_by_id('searchform').submit()
        self.assert_(is_activity_row_present(b,via='WEBUI', action='Removed',
             old_value=self.group.display_name, new_value='',
             object_='System: %s' % self.system.fqdn))
