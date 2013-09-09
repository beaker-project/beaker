
from selenium.webdriver.support.ui import Select
from bkr.server.model import SystemStatus
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base

class SystemTakeTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lc])

    def tearDown(self):
        self.browser.quit()

    def test_owner_manual_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                    owner=owner, shared=True, lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_take(system)

    """
    Tests the following scenarios for take in both Automated and Manual machines:
    * System with no groups - regular user
    * System has group, user not in group
    * System has group, user in group
    """

    def test_schedule_provision_system_has_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            job = data_setup.create_job()
            data_setup.mark_job_running(job, system=system)
        b = self.browser
        login(b)
        self.check_schedule_provision(system)

    def test_schedule_provision_system_has_user_with_group(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            data_setup.add_user_to_group(user, group)
            data_setup.add_group_to_system(system, group)
            user2 = data_setup.create_user()
            data_setup.add_user_to_group(user2, group)
            job = data_setup.create_job(owner=user2)
            data_setup.mark_job_running(job, system=system)
        b = self.browser
        login(b, user=user.user_name, password=u'testing')
        self.check_schedule_provision(system)

    def test_system_no_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_automated(system)
        self.check_schedule_provision(system)

    def test_system_no_group_manual(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_take(system)

    def test_system_has_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            # user is not in group
            data_setup.add_group_to_system(system, group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_automated(system)
        self.check_cannot_schedule_provision(system)

    def test_system_has_group_manual(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            # user is not in group
            data_setup.add_group_to_system(system, group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_manual(system)
        self.check_cannot_schedule_provision(system)

    def test_system_group_user_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            wrong_group = data_setup.create_group()
            user = data_setup.create_user(password=u'testing')
            # user is not in the same group as system
            data_setup.add_user_to_group(user, wrong_group)
            group = data_setup.create_group()
            data_setup.add_group_to_system(system, group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_automated(system)
        self.check_cannot_schedule_provision(system)

    def test_system_in_user_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            data_setup.add_user_to_group(user, group)
            data_setup.add_group_to_system(system, group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_automated(system)
        self.check_schedule_provision(system)

    def test_manual_system_in_user_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            data_setup.add_user_to_group(user, group)
            data_setup.add_group_to_system(system, group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_take(system)

    def test_automated_system_loaned_to_another_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            system.loaned = data_setup.create_user()
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_schedule_provision(system)

    def test_manual_system_loaned_to_another_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            system.loaned = data_setup.create_user()
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_manual(system)

    def go_to_system_view(self, system):
        self.browser.get(get_server_base() + 'view/%s' % system.fqdn)

    def check_take(self, system):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Take').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Reserved %s' % system.fqdn)

    def check_cannot_take_manual(self, system):
        self.go_to_system_view(system)
        b = self.browser
        # "Take" link should be absent
        b.find_element_by_xpath('//form[@name="form" and not(.//a[normalize-space(string(.))="Take"])]')
        # Try taking it directly as well:
        # https://bugzilla.redhat.com/show_bug.cgi?id=747328
        b.get(get_server_base() + 'user_change?id=%s' % system.id)
        self.assertIn('cannot reserve system',
                b.find_element_by_class_name('flash').text)

    def check_cannot_take_automated(self, system):
        self.go_to_system_view(system)
        b = self.browser
        # "Take" link should be absent
        b.find_element_by_xpath('//form[@name="form" and not(.//a[normalize-space(string(.))="Take"])]')
        # Try taking it directly as well:
        # https://bugzilla.redhat.com/show_bug.cgi?id=747328
        b.get(get_server_base() + 'user_change?id=%s' % system.id)
        self.assertIn(
                'Cannot manually reserve automated system',
                b.find_element_by_class_name('flash').text)

    def check_schedule_provision(self, system):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Provision').click()
        Select(b.find_element_by_name('prov_install'))\
            .select_by_visible_text(unicode(self.distro_tree))
        b.find_element_by_xpath('//button[text()="Schedule provision"]').click()
        self.assertIn('Success!', b.find_element_by_class_name('flash').text)

    def check_cannot_schedule_provision(self, system):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Provision').click()
        b.find_element_by_xpath('//*[@id="provision" and not(.//button[text()="Schedule Provision"])]')
        # just to be sure...
        b.find_element_by_xpath('//*[@id="provision" and not(.//button)]')
