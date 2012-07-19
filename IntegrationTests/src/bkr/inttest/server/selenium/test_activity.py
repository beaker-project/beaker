from turbogears.database import session
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_activity_row_present, \
    delete_and_confirm
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import User, DistroActivity, SystemActivity, \
    GroupActivity

class ActivityTestWD(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.distro = data_setup.create_distro()
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

    def tearDown(self):
        self.browser.quit()

    def test_can_search_by_system_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Toggle Search').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='System/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.system.fqdn)
        b.find_element_by_xpath("//input[@name='Search']").click()
        self.assert_(is_activity_row_present(b,
                object_='System: %s' % self.system.fqdn))

    def test_can_search_by_distro_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/distro')
        b.find_element_by_link_text('Toggle Search').click()
        b.find_element_by_xpath('//select[@id="activitysearch_0_table"]/option[@value="Distro/Name"]').click()
        b.find_element_by_xpath('//select[@id="activitysearch_0_operation"]/option[@value="is"]').click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.distro.name)
        b.find_element_by_xpath('//input[@name="Search"]').click()
        self.assert_(is_activity_row_present(b,
                object_='Distro: %s' % self.distro.name))

    def test_can_search_by_group_name(self):
        b = self.browser
        b.get(get_server_base() + 'activity/group')
        b.find_element_by_link_text('Toggle Search').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='Group/Name']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys(self.group.display_name)
        b.find_element_by_xpath("//input[@name='Search']").click()
        self.assert_(is_activity_row_present(b,
                object_='Group: %s' % self.group.display_name))

    def test_group_removal_is_noticed(self):
        self.group.systems.append(self.system)
        session.flush()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'groups/admin')

        b.find_element_by_xpath("//input[@name='group.text']").clear()
        b.find_element_by_xpath("//input[@name='group.text']").send_keys(self.group.group_name)
        b.find_element_by_xpath("//input[@value='Search']").submit()
        delete_and_confirm(b, "//td[preceding-sibling::td/"
            "a[normalize-space(text())='%s']]/" % self.group.group_name,
            'Remove (-)')
        should_have_deleted_msg = b.find_element_by_xpath('//body').text
        self.assert_('%s deleted' % self.group.display_name in should_have_deleted_msg)

        # Check it's recorded in System Activity
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_link_text('Toggle Search').click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_table']/option[@value='Action']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_0_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_0_value']").send_keys('Removed')
        b.find_element_by_link_text('Add ( + )').click()

        b.find_element_by_xpath("//select[@id='activitysearch_1_table']/option[@value='Old Value']").click()
        b.find_element_by_xpath("//select[@id='activitysearch_1_operation']/option[@value='is']").click()
        b.find_element_by_xpath("//input[@id='activitysearch_1_value']").send_keys(self.group.display_name)
        b.find_element_by_xpath("//input[@name='Search']").submit()
        self.assert_(is_activity_row_present(b,via='WEBUI', action='Removed',
             old_value=self.group.display_name, new_value='',
             object_='System: %s' % self.system.fqdn))
