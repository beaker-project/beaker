
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

class SystemAvailabilityTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.distro_tree = data_setup.create_distro_tree(
                    lab_controllers=[self.lc])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1401749
    def test_cant_take_broken_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.broken,
                                              lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_cannot_take(system)

    def test_own_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.automated,
                    owner=owner, lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_system_is_available(system)

    def test_own_manual_system(self):
        with session.begin():
            owner = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.manual,
                    owner=owner, lab_controller=self.lc)
        b = self.browser
        login(b, user=owner.user_name, password='testing')
        self.check_take(system)

    def test_non_shared_system(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            system = data_setup.create_system(status=SystemStatus.automated,
                    lab_controller=self.lc, shared=False)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_not_available(system)
        # same thing, as admin
        logout(b)
        login(b)
        self.check_system_is_not_available(system)

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

    def test_system_in_use_by_another_group_member(self):
        with session.begin():
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            group.add_member(user)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
            user2 = data_setup.create_user()
            group.add_member(user2)
            job = data_setup.create_job(owner=user2)
            data_setup.mark_job_running(job, system=system)
        b = self.browser
        login(b, user=user.user_name, password=u'testing')
        self.check_system_is_available(system)
        self.check_system_is_not_free(system)

    def test_shared_system(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_system_is_free(system)
        self.check_cannot_take(system)

    def test_shared_manual_system(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_take(system)

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
        # same thing, as admin
        logout(b)
        login(b)
        self.check_system_is_not_available(system)

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

    def test_system_restricted_to_different_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            wrong_group = data_setup.create_group()
            user = data_setup.create_user(password=u'testing')
            # user is not in the same group as system
            wrong_group.add_member(user)
            group = data_setup.create_group()
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_not_available(system)
        self.check_cannot_take(system)

    def test_system_restricted_to_users_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            group.add_member(user)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_system_is_available(system)
        self.check_cannot_take(system)

    def test_manual_system_restricted_to_users_group(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual,
                    shared=False, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
            group = data_setup.create_group()
            group.add_member(user)
            system.custom_access_policy.add_rule(
                    permission=SystemPermission.reserve, group=group)
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_take(system)

    def test_automated_system_loaned_to_self(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.automated,
                    shared=True, lab_controller=self.lc)
            user = data_setup.create_user(password=u'testing')
        b = self.browser
        login(b, user=user.user_name, password='testing')
        self.check_cannot_take(system)
        with session.begin():
            system.loaned = user
        self.check_take(system)

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
        b.find_element_by_xpath('//span[@class="label" and text()="Reserved"]')

    def check_cannot_take(self, system):
        self.go_to_system_view(system)
        b = self.browser
        # "Take" link should be absent
        b.find_element_by_xpath('//div[contains(@class, "system-quick-info")'
                ' and not(.//a/text()="Take")]')
