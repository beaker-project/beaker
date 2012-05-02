
from turbogears.database import session
from bkr.inttest.server.selenium import SeleniumTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import User, DistroActivity, SystemActivity

def is_activity_row_present(sel, via=u'testdata', object_=None, property_=None,
        action=None, old_value=None, new_value=None):
    row_count = int(sel.get_xpath_count('//table[@id="widget"]/tbody/tr'))
    for row in range(1, row_count + 1):
        if via and via != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[2]' % row):
            continue
        if object_ and object_ != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[4]' % row):
            continue
        if property_ and property_ != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[5]' % row):
            continue
        if action and action != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[6]' % row):
            continue
        if old_value and old_value != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[7]' % row):
            continue
        if new_value and new_value != sel.get_text('//table[@id="widget"]/tbody/tr[%d]/td[8]' % row):
            continue
        return True
    return False

class ActivityTest(SeleniumTestCase):

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
        self.selenium = self.get_selenium()
        self.selenium.start()

    def tearDown(self):
        self.selenium.stop()

    def test_shows_all_activity(self):
        sel = self.selenium
        sel.open('activity/')
        self.assert_(is_activity_row_present(sel,
                object_='Distro: %s' % self.distro.name))
        self.assert_(is_activity_row_present(sel,
                object_='System: %s' % self.system.fqdn))

    def test_can_search_by_system_name(self):
        sel = self.selenium
        sel.open('activity/')
        sel.click('link=Toggle Search')
        sel.select('activitysearch_0_table', 'System/Name')
        sel.select('activitysearch_0_operation', 'is')
        sel.type('activitysearch_0_value', self.system.fqdn)
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assert_(not is_activity_row_present(sel,
                object_='Distro: %s' % self.distro.name))
        self.assert_(is_activity_row_present(sel,
                object_='System: %s' % self.system.fqdn))

    def test_can_search_by_distro_name(self):
        sel = self.selenium
        sel.open('activity/')
        sel.click('link=Toggle Search')
        sel.select('activitysearch_0_table', 'Distro/Name')
        sel.select('activitysearch_0_operation', 'is')
        sel.type('activitysearch_0_value', self.distro.name)
        sel.click('Search')
        sel.wait_for_page_to_load('30000')
        self.assert_(is_activity_row_present(sel,
                object_='Distro: %s' % self.distro.name))
        self.assert_(not is_activity_row_present(sel,
                object_='System: %s' % self.system.fqdn))
