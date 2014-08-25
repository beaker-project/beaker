
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present, \
        click_menu_item, logout
from bkr.inttest import data_setup
from bkr.server.tools import beakerd
from bkr.server.model import Job, TaskStatus


class RemoveUser(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_remove_user(self):
        with session.begin():
            user = data_setup.create_user(user_name =
                                          data_setup.unique_name('aaaaa%s'))
        b = self.browser
        login(b)
        b.get(get_server_base() + 'users')
        b.find_element_by_xpath('//a[@href="remove?id=%d"]' %user.user_id).click()
        self.assertEquals(b.find_element_by_class_name('flash').text,
                          'User %s removed' % user.user_name)

    def test_remove_user_job_cancel(self):
        with session.begin():
            user = data_setup.create_user(user_name =
                                          data_setup.unique_name('aaaaa%s'))
            job = data_setup.create_job(owner=user)
            data_setup.mark_job_running(job)

        b = self.browser
        login(b)
        b.get(get_server_base() + 'users')
        b.find_element_by_xpath('//a[@href="remove?id=%d"]' %user.user_id).click()
        # XXX: not necessary, but doing it here to buy time, since sometimes the
        # job cancellation seems to take a while
        logout(b)

        # reflect the change in recipe task status when
        # update_dirty_jobs() is called
        session.expunge_all()
        beakerd.update_dirty_jobs()

        with session.begin():
            job = Job.by_id(job.id)
            self.assertEquals(job.status, TaskStatus.cancelled)
            self.assertIn('User %s removed' % user.user_name,
                          job.recipesets[0].recipes[0].tasks[0].results[0].log)
