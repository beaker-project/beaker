
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from selenium.webdriver.support.ui import Select
from bkr.server.model import SystemStatus, SystemPermission
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout, \
        search_for_system, check_system_search_results
from turbogears.database import session
from bkr.inttest import data_setup, get_server_base

# Provision messages

MSG_ANONYMOUS = "You are not logged in."
MSG_NO_ACCESS = "You do not have access to provision this system."
MSG_LOST_ACCESS = "After returning this system, you will no longer be able to provision it."
MSG_MANUAL = "Reserve this system to provision it."
MSG_MANUAL_RESERVED = "System will be provisioned directly."
MSG_AUTO = "Provisioning will use a scheduled job. Borrow and reserve this system to provision it directly instead."
MSG_AUTO_BORROWED = "Provisioning will use a scheduled job. Reserve this system to provision it directly instead."
MSG_AUTO_RESERVED = "System will be provisioned directly. Return this system to use a scheduled job instead."


class SystemAvailabilityTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lc])

    def tearDown(self):
        self.browser.quit()

    def test_anonymous(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                    owner=owner, lab_controller=self.lc)
        b = self.browser
        self.check_cannot_provision(system, MSG_ANONYMOUS)

    def test_own_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.automated,
                    owner=owner, lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_own_manual_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                    owner=owner, lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_cannot_provision(system, MSG_MANUAL)
        self.check_take(system)
        self.check_manual_provision(system, MSG_MANUAL_RESERVED)

    def test_non_shared_system(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.automated,
                    lab_controller=self.lc, shared=False)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_not_available(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)
        # same thing, as admin
        logout(b)
        login(b)
        self.check_system_is_not_available(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)

    def test_system_in_use_by_another_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            job = data_setup.create_job()
            data_setup.mark_job_running(job, system=system)
        b = self.browser
        login(b)
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_system_in_use_by_another_group_member(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            data_setup.add_user_to_group(user, group)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
            user2 = data_setup.create_user()
            data_setup.add_user_to_group(user2, group)
            job = data_setup.create_job(owner=user2)
            data_setup.mark_job_running(job, system=system)
        b = self.browser
        login(b, user=user.user_name, password=u'testing')
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_shared_system(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_system_is_free(system)
        self.check_cannot_take_automated(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_shared_manual_system(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_provision(system, MSG_MANUAL)
        self.check_take(system)
        self.check_manual_provision(system, MSG_MANUAL_RESERVED)

    def test_system_restricted_to_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            # user is not in group
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_not_available(system)
        self.check_cannot_take(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)
        # same thing, as admin
        logout(b)
        login(b)
        self.check_system_is_not_available(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)

    def test_manual_system_restricted_to_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            # user is not in group
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)

    def test_system_restricted_to_different_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            wrong_group = data_setup.create_group()
            user = data_setup.create_user(password=u'testing')
            # user is not in the same group as system
            data_setup.add_user_to_group(user, wrong_group)
            group = data_setup.create_group()
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_not_available(system)
        self.check_cannot_take(system)
        self.check_cannot_provision(system, MSG_NO_ACCESS)

    def test_system_restricted_to_users_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            data_setup.add_user_to_group(user, group)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_cannot_take_automated(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_manual_system_restricted_to_users_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            data_setup.add_user_to_group(user, group)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_provision(system, MSG_MANUAL)
        self.check_take(system)
        self.check_manual_provision(system, MSG_MANUAL_RESERVED)

    def test_automated_system_loaned_to_self(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take_automated(system)
        self.check_schedule_provision(system, MSG_AUTO)
        with session.begin():
            system.loaned = user
        self.check_schedule_provision(system, MSG_AUTO_BORROWED)
        self.check_take(system)
        self.check_manual_provision(system, MSG_AUTO_RESERVED)

    def test_automated_system_loaned_to_another_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            system.loaned = data_setup.create_user()
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)
        self.check_cannot_take(system)
        self.check_schedule_provision(system, MSG_AUTO)

    def test_manual_system_loaned_to_another_user(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            system.loaned = data_setup.create_user()
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)
        self.check_cannot_take(system)
        self.check_cannot_provision(system, MSG_MANUAL)

    # https://bugzilla.redhat.com/show_bug.cgi?id=920018
    def test_lc_disabled(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            self.lc.disabled = True
        b = self.browser
        login(b)
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)

    def check_system_is_available(self, system):
        """
        Checks that the system can be found by searching on the Available page, 
        indicating that the logged-in user has access to reserve it.
        """
        b = self.browser
        b.get(get_server_base() + 'available')
        search_for_system(b, system)
        check_system_search_results(b, present=[system])

    def check_system_is_not_available(self, system):
        b = self.browser
        b.get(get_server_base() + 'available')
        search_for_system(b, system)
        check_system_search_results(b, absent=[system])

    def check_system_is_free(self, system):
        """
        Checks that the system can be found by searching on the Free page, 
        indicating that the logged-in user has access to reserve it and it is 
        currently not in use.
        """
        b = self.browser
        b.get(get_server_base() + 'free')
        search_for_system(b, system)
        check_system_search_results(b, present=[system])

    def check_system_is_not_free(self, system):
        b = self.browser
        b.get(get_server_base() + 'free')
        search_for_system(b, system)
        check_system_search_results(b, absent=[system])

    def go_to_system_view(self, system):
        self.browser.get(get_server_base() + 'view/%s' % system.fqdn)

    def check_take(self, system):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Take').click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Reserved %s' % system.fqdn)

    def check_cannot_take(self, system):
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

    def check_cannot_provision(self, system, message):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Provision').click()
        # Check for a specific info message
        if message is not None:
            b.find_element_by_xpath('//span[normalize-space(text())="%s"]' % message)
        # Ensure provisioning is not offered
        b.find_element_by_xpath('//*[@id="provision" and not(.//button)]')


    # XXX There's a *lot* of logic spread across controllers.py,
    # the system_provision.kid template and the SystemProvision
    #
    def check_schedule_provision(self, system, message):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Provision').click()
        # Check for a specific info message
        if message is not None:
            b.find_element_by_xpath('//span[normalize-space(text())="%s"]' % message)
        # Ensure the provision form is configured to schedule the provision
        b.find_element_by_xpath('//*[@id="scheduled-provisioning"]')
        # Ensure the scheduled provision settings are included
        b.find_element_by_xpath('//*[@id="scheduled-provisioning-settings"]')
        # Ensure only scheduled provisioning is offered
        b.find_element_by_xpath('//*[@id="provision" and '
                                    './/button[text()="Schedule provision"] and '
                                    'not(.//button[text()="Provision"])]')
        # Schedule the provisioning job
        Select(b.find_element_by_name('prov_install'))\
            .select_by_visible_text(unicode(self.distro_tree))
        b.find_element_by_xpath('//button[text()="Schedule provision"]').click()
        self.assertIn('Success!', b.find_element_by_class_name('flash').text)

    def check_manual_provision(self, system, message):
        self.go_to_system_view(system)
        b = self.browser
        b.find_element_by_link_text('Provision').click()
        # Check for a specific info message
        if message is not None:
            b.find_element_by_xpath('//span[normalize-space(text())="%s"]' % message)
        # Ensure the provision panel is configured for direct provisioning
        b.find_element_by_xpath('//*[@id="direct-provisioning"]')
        # Ensure the direct provision settings are included
        b.find_element_by_xpath('//*[@id="direct-provisioning-settings"]')
        # Ensure only manual provisioning is offered
        b.find_element_by_xpath('//*[@id="provision" and '
                                    './/button[text()="Provision"] and '
                                    'not(.//button[text()="Schedule provision"])]')
