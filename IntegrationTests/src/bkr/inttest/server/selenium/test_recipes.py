
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time
import datetime
import logging
import re
import urlparse
import requests
import lxml.etree
from turbogears.database import session

from bkr.server.model import TaskStatus, TaskResult, RecipeTaskResult, \
    Task, RecipeTaskComment, RecipeTaskResultComment, RecipeTask, \
    CommandStatus, RecipeReservationCondition, LogRecipeTask
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, is_text_present
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.assertions import assert_sorted
from bkr.inttest.server.requests_utils import post_json, patch_json, \
        put_json, login as requests_login
from bkr.inttest.assertions import assert_datetime_within

class TestRecipesDataGrid(WebDriverTestCase):

    log = logging.getLogger(__name__ + '.TestRecipesIndex')

    @classmethod
    def setUpClass(cls):
        # create a bunch of jobs
        with session.begin():
            cls.user = user = data_setup.create_user(password='password')
            arches = [u'i386', u'x86_64', u'ia64']
            distros = [data_setup.create_distro(name=name) for name in
                    [u'DAN5-Server-U5', u'DAN5-Client-U5', u'DAN6-U1', u'DAN6-RC3']]
            for arch in arches:
                for distro in distros:
                    distro_tree = data_setup.create_distro_tree(distro=distro, arch=arch)
                    data_setup.create_job(owner=user, distro_tree=distro_tree)
                    data_setup.create_completed_job(owner=user, distro_tree=distro_tree)

    def setUp(self):
        self.browser = self.get_browser()
        login(self.browser, user=self.user.user_name, password='password')

    # see https://bugzilla.redhat.com/show_bug.cgi?id=629147
    def check_column_sort(self, column, sort_key=None):
        b = self.browser
        b.get(get_server_base() + 'recipes/mine')
        b.find_element_by_xpath('//table[@id="widget"]/thead//th[%d]//a[@href]' % column).click()
        row_count = len(b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = [b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column)).text
                       for row in range(1, row_count + 1)]
        assert_sorted(cell_values, key=sort_key)

    def test_can_sort_by_whiteboard(self):
        self.check_column_sort(2)

    def test_can_sort_by_arch(self):
        self.check_column_sort(3)

    def test_can_sort_by_system(self):
        self.check_column_sort(4)

    def test_can_sort_by_status(self):
        order = ['New', 'Processed', 'Queued', 'Scheduled', 'Waiting',
                'Running', 'Completed', 'Cancelled', 'Aborted']
        self.check_column_sort(7, sort_key=lambda status: order.index(status))

    def test_can_sort_by_result(self):
        self.check_column_sort(8)

    # this version is different since the cell values will be like ['R:1', 'R:10', ...]
    def test_can_sort_by_id(self):
        column = 1
        b = self.browser
        b.get(get_server_base() + 'recipes/mine')
        b.find_element_by_xpath('//table[@id="widget"]/thead//th[%d]//a[@href]' % column).click()
        row_count = len(b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr/td[%d]' % column))
        self.assertEquals(row_count, 24)
        cell_values = []
        for row in range(1, row_count + 1):
            raw_value = b.find_element_by_xpath('//table[@id="widget"]/tbody/tr[%d]/td[%d]' % (row, column)).text
            m = re.match(r'R:(\d+)$', raw_value)
            assert m.group(1)
            cell_values.append(int(m.group(1)))
        assert_sorted(cell_values)


def go_to_recipe_view(browser, recipe, tab=None):
    b = browser
    b.get(get_server_base() + 'recipes/%s' % recipe.id)
    if tab:
        b.find_element_by_xpath('//ul[contains(@class, "recipe-nav")]'
                '//a[text()="%s"]' % tab).click()


class TestRecipeView(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.user = user = data_setup.create_user(display_name=u'Bob Brown',
                    password='password')
            self.lab_controller = data_setup.create_labcontroller()
            self.system_owner = data_setup.create_user()
            self.system = data_setup.create_system(owner=self.system_owner, arch=u'x86_64',
                    lab_controller=self.lab_controller)
            self.distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                    osmajor=u'PurpleUmbrellaLinux5', osminor=u'11',
                    variant=u'Server')
            self.job = data_setup.create_completed_job(owner=user,
                    distro_tree=self.distro_tree, server_log=True)
            self.recipe = self.job.recipesets[0].recipes[0]
            for recipe in self.job.all_recipes:
                recipe.system = self.system
        self.browser = self.get_browser()

    def test_recipe_page_does_not_error_when_installation_is_none(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe, task_status=TaskStatus.cancelled)
            job.update_status()
            # old recipes before Beaker 25.0 may have no installation row
            recipe.installation = None
        b = self.browser
        login(b)
        go_to_recipe_view(b, recipe, tab="Installation")
        self.assertEqual(
            b.find_element_by_xpath('//div[@class="recipe-installation-progress"]').text,
            "No installation progress reported.")

    # https://bugzilla.redhat.com/show_bug.cgi?id=1362595
    def test_report_system_problem_for_recipe_works(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user, distro_tree=self.distro_tree)
            recipe = job.recipesets[0].recipes[0]
            start_time = datetime.datetime.utcnow()
            finish_time = start_time + datetime.timedelta(seconds=1)
            system = data_setup.create_system(arch=u'x86_64',
                    fqdn=u'snoopy.example.com',
                    lab_controller=self.lab_controller)
            data_setup.mark_recipe_complete(recipe, system=system,
                    result=TaskResult.pass_,
                    start_time=start_time, finish_time=finish_time)

        b = self.browser
        login(b)
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('//button[@aria-label="System actions"]').click()

        b.find_element_by_xpath('//a[@class="report-problem"]').click()
        b.find_element_by_name('message').send_keys(u'a' + u'\u044f' * 100)
        b.find_element_by_xpath('//button[text()="Report"]').click()
        b.find_element_by_xpath('//div[contains(@class, "alert-success")]'
                '/h4[text()="Report sent"]')


    # https://bugzilla.redhat.com/show_bug.cgi?id=1335343
    def test_page_updates_itself_while_recipe_is_running(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                    distro_name=u'PurpleUmbrellaLinux5.11-20160428.0',
                    variant=u'Server')
            job = data_setup.create_job(owner=self.user, distro_tree=distro_tree)
            recipe = job.recipesets[0].recipes[0]
        b = self.browser
        # Open the recipe page while the recipe is still Queued.
        go_to_recipe_view(b, recipe)
        # Let the recipe finish (in reality there are of course many 
        # intermediate steps here, but jumping straight to a finished recipe 
        # still lets us check that all the pieces are updating themselves).
        with session.begin():
            start_time = datetime.datetime.utcnow()
            finish_time = start_time + datetime.timedelta(seconds=1)
            system = data_setup.create_system(arch=u'x86_64',
                    fqdn=u'pewlett-hackard-x004.example.com',
                    lab_controller=self.lab_controller)
            data_setup.mark_recipe_complete(recipe, system=system,
                    result=TaskResult.pass_,
                    start_time=start_time, finish_time=finish_time)
        # Wait for the page to re-fetch the recipe JSON.
        time.sleep(40)
        # Check that everything has updated itself.
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-summary"]/p[1]').text,
                'Started a few seconds ago and finished in 00:00:01.')
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-summary"]/p[2]').text,
                'Using PurpleUmbrellaLinux5.11-20160428.0 Server x86_64\n'
                'on pewlett-hackard-x004.example.com\n.')
        # Check that Report problem button displays
        # https://bugzilla.redhat.com/show_bug.cgi?id=1362595
        b.find_element_by_xpath('//a[@class="report-problem"]')
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-installation-summary"]/div[1]').text,
                'Installation of PurpleUmbrellaLinux5.11-20160428.0 Server x86_64 finished.')
        b.find_element_by_xpath('//div[@class="recipe-installation-status"]'
                '/span[@class="label label-success" and text()="Completed"]')
        b.find_element_by_xpath('//div[@class="recipe-installation-progress"]'
                '//td[contains(text(), "Netboot configured")]')
        b.find_element_by_xpath('//div[@class="recipe-installation-progress"]'
                '//td[contains(text(), "System rebooted")]')
        b.find_element_by_xpath('//div[@class="recipe-installation-progress"]'
                '//td[contains(text(), "Installation started")]')
        b.find_element_by_xpath('//div[@class="recipe-installation-progress"]'
                '//td[contains(text(), "Installation completed")]')
        b.find_element_by_xpath('//div[@class="recipe-installation-progress"]'
                '//td[contains(text(), "Post-install tasks completed")]')
        b.find_element_by_xpath('//ul[contains(@class, "recipe-nav")]'
                '//a[text()="Tasks"]').click()
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-tasks-summary"]/div[1]').text,
                'Pass with 1 out of 1 tasks finished.')
        b.find_element_by_xpath('//div[@class="recipe-progress"]/span[text()="100%"]')
        b.find_element_by_xpath('//div[@class="recipe-progress"]'
                '/div[@class="progress"]/a[@class="bar bar-result-pass" and @style="width: 100%;"]')
        task_element = b.find_element_by_xpath('//div[@id="task%s"]' % recipe.tasks[0].id)
        self.assertEqual(
                task_element.find_element_by_class_name('recipe-task-status').text,
                'Pass')
        task_element.find_element_by_class_name('task-icon').click()
        result_element = task_element.find_element_by_class_name('recipe-task-result')
        result_element.find_element_by_xpath('div[@class="task-result-id"'
                ' and normalize-space(string(.))="%s"]' % recipe.tasks[0].results[0].t_id)
        result_element.find_element_by_xpath('div[@class="task-result-result"]'
                '/span[@class="label label-result-pass" and text()="Pass"]')
        b.find_element_by_xpath('//ul[contains(@class, "recipe-nav")]'
                '//a[text()="Reservation"]').click()
        self.assertEqual(
                b.find_element_by_xpath('//div[@id="reservation"]/div/p').text,
                'The system was not reserved at the end of the recipe.')

    def test_page_header(self):
        with session.begin():
            job = data_setup.create_job(num_recipes=2, num_guestrecipes=1)
            recipe = job.recipesets[0].recipes[1]
        b = self.browser
        go_to_recipe_view(b, recipe)
        subtitle = b.find_element_by_xpath('//div[@class="page-header"]/h1/small')
        self.assertEqual(subtitle.text, '2 of 3 recipes in %s' % job.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1314271
    def test_view_deleted_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            recipetask = recipe.tasks[0]
            job.deleted = datetime.datetime.utcnow()
        b = self.browser
        b.get(get_server_base() + 'recipes/%s#task%s'
                % (recipe.id, recipe.tasks[0].id))
        self.assertIn('This job has been deleted.',
                b.find_element_by_class_name('alert-warning').text)
        task_row = b.find_element_by_css_selector('#task%s .recipe-task-details.collapse.in'
                % recipe.tasks[0].id)
        task_row.find_element_by_xpath('.//button[normalize-space(string(.))="Results" and @disabled="disabled"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1364288
    def test_view_virt_recipe(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                    distro_name=u'PurpleUmbrellaLinux5.11-20160428.1',
                    variant=u'Server')
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe, virt=True)
            recipe.resource.fqdn = u'example.openstacklocal.invalid'
        b = self.browser
        go_to_recipe_view(b, recipe)
        self.assertEqual('Using PurpleUmbrellaLinux5.11-20160428.1 Server x86_64\n'
            'on example.openstacklocal.invalid\n\n(OpenStack instance %s).' % recipe.resource.instance_id,
            b.find_element_by_xpath('//div[@class="recipe-summary"]/p[2]').text)

        # Ensure Report problem button not showing for virtual system
        # https://bugzilla.redhat.com/show_bug.cgi?id=1362595
        b.find_element_by_xpath('//body[not(.//a[@class="report-problem"])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1390409
    def test_view_virt_recipe_when_the_hostname_is_not_known_yet(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                    distro_name=u'PurpleUmbrellaLinux5.11-20160428.2',
                    variant=u'Server')
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe, virt=True)
        b = self.browser
        go_to_recipe_view(b, recipe)
        self.assertEqual('Using PurpleUmbrellaLinux5.11-20160428.2 Server x86_64\n'
            'on OpenStack instance %s.' % recipe.resource.instance_id,
            b.find_element_by_xpath('//div[@class="recipe-summary"]/p[2]').text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1412878
    def test_link_to_httpthesystem(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_running(recipe)
        b = self.browser
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath(
                '//span[contains(@class, "fqdn")]//a[contains(., "View http://%s/")]'
                % recipe.resource.fqdn)
        # Once the recipe is finished there is nothing running on the system to 
        # link to anymore, so the link should disappear.
        with session.begin():
            data_setup.mark_recipe_complete(recipe, only=True)
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath(
                '//span[contains(@class, "fqdn") and '
                'not(.//a[contains(., "View http://")])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=626529
    def test_guest_recipe_info(self):
        with session.begin():
            job = data_setup.create_job(num_recipes=1, num_guestrecipes=1)
            guest = job.recipesets[0].recipes[0].guests[0]
            guest.guestname = u'guest1'
            guest.guestargs = u'--kvm --ram 1024'
        b = self.browser
        go_to_recipe_view(b, guest, tab='Installation')
        summary = b.find_element_by_xpath('//div[@class="recipe-summary"]/p[2]').text
        b.find_element_by_xpath('//div[@id="installation"]//button[text()="Settings"]').click()
        self.assertIn('Guest recipe hosted by %s.' % guest.hostrecipe.t_id, summary)
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-installation-settings"]'
                    '/div[preceding-sibling::h4/text()="Guest Name"]/code').text,
                'guest1')
        self.assertEqual(
                b.find_element_by_xpath('//div[@class="recipe-installation-settings"]'
                    '/div[preceding-sibling::h4/text()="Guest Arguments for virt-install"]/code').text,
                '--kvm --ram 1024')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1326562
    def test_recipe_view_shows_external_task_results(self):
        with session.begin():
            recipe = data_setup.create_recipe(task_name=u'/distribution/check-install')
            external_task = RecipeTask.from_fetch_url(
                url='git://example.com/externaltasks/example#master',
                subdir='examples')
            recipe.tasks.extend([external_task])
            data_setup.create_job_for_recipes([recipe], whiteboard='job with external tasks')
            data_setup.mark_recipe_complete(recipe, result=TaskResult.warn, task_status=TaskStatus.aborted)

        b = self.browser
        go_to_recipe_view(b, recipe=recipe, tab='Tasks')
        b.find_element_by_xpath('//div[@class="task-result-path"]/.[contains(text(), "%s")]' % external_task.fetch_url)
        b.find_element_by_xpath('//span[@class="task-name"]/.[contains(text(), "%s")]' % external_task.fetch_url)

    def test_possible_systems(self):
        with session.begin():
            self.system.user = self.user
            queued_job = data_setup.create_job(owner=self.user,
                    distro_tree=self.distro_tree)
            data_setup.mark_job_queued(queued_job)
            recipe = queued_job.recipesets[0].recipes[0]
            recipe.systems[:] = [self.system]
        b = self.browser
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('//div[@class="recipe-summary"]'
                '//a[normalize-space(text())="1 possible system"]').click()
        # Make sure our system link is there
        b.find_element_by_link_text(self.system.fqdn)
        # Make sure our user link is there
        b.find_element_by_link_text(self.system.user.user_name)
        # Make sure the System count is correct
        system_rows = b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr')
        self.assert_(len(system_rows) == 1)

    def test_possible_systems_including_loans(self):
        with session.begin():
            self.system.loaned = self.user
            queued_job = data_setup.create_job(owner=self.user,
                                               distro_tree=self.distro_tree)
            data_setup.mark_job_queued(queued_job)
            recipe = queued_job.recipesets[0].recipes[0]
            recipe.systems[:] = [self.system]
        b = self.browser
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('//div[@class="recipe-summary"]'
                                '//a[normalize-space(text())="1 possible system"]').click()
        # Make sure our system link is there
        b.find_element_by_link_text(self.system.fqdn)
        # Make sure loaned user is there
        b.find_element_by_xpath("//td[contains(text(), '%s')]" % self.system.loaned.user_name)
        # Make sure the System count is correct
        system_rows = b.find_elements_by_xpath('//table[@id="widget"]/tbody/tr')
        self.assert_(len(system_rows) == 1)

    def test_clone_recipe(self):
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe)
        b.find_element_by_link_text("Clone").click()
        b.find_element_by_xpath('//h1[normalize-space(text())="Clone Recipeset %s"]' %
                self.recipe.recipeset.id)

    def test_log_url_looks_right(self):
        b = self.browser
        go_to_recipe_view(b, self.recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        log_link = tab.find_element_by_xpath('//span[@class="main-log"]/a')
        self.assertEquals(log_link.get_attribute('href'),
            get_server_base() + 'recipes/%s/logs/recipe_path/dummy.txt' %
                    self.recipe.id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1072133
    def test_watchdog_time_remaining_display(self):
        b = self.browser
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe], owner=self.user)
            data_setup.mark_job_running(job)
            recipe.watchdog.kill_time = (datetime.datetime.utcnow() +
                    datetime.timedelta(seconds=83 * 60 + 30))
        go_to_recipe_view(b, recipe)
        duration = b.find_element_by_class_name('recipe-watchdog-time-remaining')
        self.assertRegexpMatches(duration.text, r'^Remaining watchdog time: 01:\d\d:\d\d')
        with session.begin():
            recipe.watchdog.kill_time = (datetime.datetime.utcnow() +
                    datetime.timedelta(days=2, seconds=83 * 60 + 30))
        go_to_recipe_view(b, recipe)
        duration = b.find_element_by_class_name('recipe-watchdog-time-remaining')
        self.assertRegexpMatches(duration.text, r'^Remaining watchdog time: 49:\d\d:\d\d')

    def test_task_versions_are_shown(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            recipetask = recipe.tasks[0]
            recipetask.version = u'1.10-23'
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        self.assertIn('1.10-23', b.find_element_by_xpath('//div[@id="task%s"]'
                '//span[contains(@class, "task-version")]' % recipetask.id).text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1352760
    def test_task_progress_bar_chunks(self):
        with session.begin():
            recipe = data_setup.create_recipe(task_list=[
                data_setup.create_task(name=u'/chunk/one'),
                data_setup.create_task(name=u'/chunk/two'),
                data_setup.create_task(name=u'/chunk/three'),
            ])
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_complete(recipe)
            recipe.tasks[0].results[0].result = TaskResult.pass_
            recipe.tasks[0].result = TaskResult.pass_
            recipe.tasks[1].results[0].result = TaskResult.fail
            recipe.tasks[1].result = TaskResult.fail
            recipe.tasks[2].results[0].result = TaskResult.warn
            recipe.tasks[2].result = TaskResult.warn
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        chunks = b.find_elements_by_xpath('//div[@class="recipe-progress"]/div[@class="progress"]/*')
        self.assertEqual(chunks[0].get_attribute('href'),
                get_server_base() + 'recipes/%s#task%s' % (recipe.id, recipe.tasks[0].id))
        self.assertEqual(chunks[0].get_attribute('title'),
                '/chunk/one')
        self.assertEqual(chunks[0].get_attribute('class'), 'bar bar-result-pass')
        self.assertEqual(chunks[1].get_attribute('href'),
                get_server_base() + 'recipes/%s#task%s' % (recipe.id, recipe.tasks[1].id))
        self.assertEqual(chunks[1].get_attribute('title'),
                '/chunk/two')
        self.assertEqual(chunks[1].get_attribute('class'), 'bar bar-result-fail')
        self.assertEqual(chunks[2].get_attribute('href'),
                get_server_base() + 'recipes/%s#task%s' % (recipe.id, recipe.tasks[2].id))
        self.assertEqual(chunks[2].get_attribute('title'),
                '/chunk/three')
        self.assertEqual(chunks[2].get_attribute('class'), 'bar bar-result-warn')

    def test_anonymous_cannot_edit_whiteboard(self):
        b = self.browser
        go_to_recipe_view(b, self.recipe)
        b.find_element_by_xpath('//div[@class="recipe-page-header" and '
                'not(.//button[normalize-space(string(.))="Edit"])]')

    def test_authenticated_user_can_edit_whiteboard(self):
        with session.begin():
            job = data_setup.create_job(owner=self.user)
            recipe = job.recipesets[0].recipes[0]
        b = self.browser
        login(b)
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('whiteboard').clear()
        modal.find_element_by_name('whiteboard').send_keys('testwhiteboard')
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.refresh(recipe)
            self.assertEqual(recipe.whiteboard, 'testwhiteboard')

    def test_shows_reservation_tab_when_reserved(self):
        with session.begin():
            recipe = data_setup.create_recipe(reservesys=True)
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe)
            job.update_status()
            self.assertEqual(recipe.status, TaskStatus.reserved)
        b = self.browser
        go_to_recipe_view(b, recipe)
        b.find_element_by_css_selector('#reservation.active')
        _, fragment = urlparse.urldefrag(b.current_url)
        self.assertEquals(fragment, 'reservation')

    def test_shows_installation_tab_while_installing(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe)
        b = self.browser
        go_to_recipe_view(b, recipe)
        b.find_element_by_css_selector('#installation.active')
        _, fragment = urlparse.urldefrag(b.current_url)
        self.assertEquals(fragment, 'installation')

    def test_first_failed_task_should_expand_when_first_loading(self):
        with session.begin():
            recipe = data_setup.create_recipe(task_list=[
                Task.by_name(u'/distribution/check-install'),
                Task.by_name(u'/distribution/reservesys')
            ])
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe, result=TaskResult.fail)
            job.update_status()
        b = self.browser
        go_to_recipe_view(b, recipe)
        # The in class is an indication that a task is expanded.
        b.find_element_by_css_selector('#task%s .recipe-task-details.collapse.in'
                % recipe.tasks[0].id)
        _, fragment = urlparse.urldefrag(b.current_url)
        self.assertEquals(fragment, 'task%s' % recipe.tasks[0].id)

    def test_task_without_failed_results_should_not_expand(self):
        with session.begin():
            recipe = data_setup.create_recipe(task_list=[
                Task.by_name(u'/distribution/check-install'),
                Task.by_name(u'/distribution/reservesys')
            ])
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe, result=TaskResult.pass_)
            job.update_status()
        b = self.browser
        go_to_recipe_view(b, recipe)
        for task in recipe.tasks:
            b.find_element_by_xpath('//div[@id="recipe-task-details-%s" and '
                    'not(contains(@class, "in"))]' % task.id)
        _, fragment = urlparse.urldefrag(b.current_url)
        self.assertEquals(fragment, 'tasks')

    def test_tasks_are_expanded_according_to_anchor(self):
        with session.begin():
            recipe = data_setup.create_recipe(num_tasks=2)
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_tasks_finished(recipe, result=TaskResult.pass_)
            job.update_status()
        b = self.browser
        b.get(get_server_base() + 'recipes/%s#task%s,task%s'
                % (recipe.id, recipe.tasks[0].id, recipe.tasks[1].id))
        b.find_element_by_css_selector('#task%s .recipe-task-details.collapse.in'
                % recipe.tasks[0].id)
        b.find_element_by_css_selector('#task%s .recipe-task-details.collapse.in'
                % recipe.tasks[1].id)
        task_icon = b.find_element_by_css_selector('#task%s .recipe-task-summary .task-icon a'
               % recipe.tasks[0].id)
        self.assertNotIn('collapsed', task_icon.get_attribute('class'))
        task_icon = b.find_element_by_css_selector('#task%s .recipe-task-summary .task-icon a'
                % recipe.tasks[1].id)
        self.assertNotIn('collapsed', task_icon.get_attribute('class'))

    def test_unrecognised_anchor_is_replaced_with_default(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe)
        b = self.browser
        b.get(get_server_base() + 'recipes/%s#no-such-anchor-exists' % recipe.id)
        b.find_element_by_css_selector('#installation.active')
        _, fragment = urlparse.urldefrag(b.current_url)
        self.assertEquals(fragment, 'installation')

    # https://bugzilla.redhat.com/show_bug.cgi?id=706435
    def test_task_start_time_is_localised(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_running(recipe)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        tab = b.find_element_by_id('tasks')
        start_time = tab.find_element_by_xpath('//div[@id="task%s"]'
                '//div[@class="task-start-time"]/time' % recipe.tasks[0].id)
        self.check_datetime_localised(start_time.get_attribute('title'))

    def check_datetime_localised(self, dt):
        self.assert_(re.match(r'\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d [-+]\d\d:\d\d$', dt),
                '%r does not look like a localised datetime' % dt)

    def test_opening_recipe_page_marks_it_as_reviewed(self):
        # ... but only if it's already finished or Reserved.
        with session.begin():
            recipe = self.recipe
            self.assertEqual(recipe.get_reviewed_state(self.user), False)
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('//h1[contains(string(.), "%s")]' % recipe.t_id)
        with session.begin():
            self.assertEqual(recipe.get_reviewed_state(self.user), True)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1376645
    def test_opening_running_recipe_does_not_mark_it_reviewed(self):
        with session.begin():
            job = data_setup.create_running_job()
            recipe = job.recipesets[0].recipes[0]
            self.assertEqual(recipe.get_reviewed_state(self.user), False)
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        go_to_recipe_view(b, recipe)
        b.find_element_by_xpath('//h1[contains(string(.), "%s")]' % recipe.t_id)
        with session.begin():
            self.assertEqual(recipe.get_reviewed_state(self.user), False)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1360589
    def test_completed_and_viewed_recipe_marked_as_reviewed(self):
        with session.begin():
            job = data_setup.create_running_job()
            recipe = job.recipesets[0].recipes[0]

        b = self.browser
        login(b, user=self.user.user_name, password='password')
        go_to_recipe_view(b, recipe)

        with session.begin():
            # mark completed
            data_setup.mark_recipe_complete(recipe, only=True)
        # wait for recipes page to refresh
        time.sleep(40)
        with session.begin():
            # assert that completed recipe is marked reviewed
            self.assertTrue(recipe.get_reviewed_state(self.user))

    def test_anonymous_can_see_recipetask_comments(self):
        with session.begin():
            recipe = data_setup.create_recipe(num_tasks=2)
            job = data_setup.create_job_for_recipes([recipe])
            recipetask = recipe.tasks[0]
            # comment on first recipe task, no comments on second task
            recipetask.comments.append(RecipeTaskComment(
                    comment=u'something', user=data_setup.create_user()))
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        # first task row should have comments link
        tab = b.find_element_by_id('tasks')
        comments_link = tab.find_element_by_xpath(
                '//div[@id="task%s"]//div[@class="task-comments"]'
                '/div/a[@class="comments-link"]' % recipetask.id).text
        self.assertEqual(comments_link, '1') # it's actually "1 <commenticon>"
        # second recipe task should have no comments link
        tab.find_element_by_xpath(
                '//div[@id="task%s"]//div[@class="task-comments" and '
                'not(./div/a)]' % recipe.tasks[1].id)

    def test_authenticated_user_can_comment_recipetask(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            recipetask = recipe.tasks[0]
            # no special permissions required to comment
            user = data_setup.create_user(password=u'otheruser')
        comment_text = u'comments are fun'
        b = self.browser
        login(b, user=user.user_name, password='otheruser')
        go_to_recipe_view(b, recipe, tab='Tasks')
        tab = b.find_element_by_id('tasks')
        tab.find_element_by_xpath('//div[@class="task-comments"]'
                '/div/a[@class="comments-link"]').click()
        popover = b.find_element_by_class_name('popover')
        popover.find_element_by_name('comment').send_keys(comment_text)
        popover.find_element_by_tag_name('form').submit()
        # check if the commit is in the comments list indicating the comment is submitted
        popover.find_element_by_xpath('//div[@class="comments"]//div[@class="comment"]'
            '/p[2][text()="%s"]' % comment_text)
        self.assertEqual(popover.find_element_by_name('comment').text, '')
        with session.begin():
            session.expire_all()
            self.assertEqual(recipetask.comments[0].user, user)
            self.assertEqual(recipetask.comments[0].comment, comment_text)
        # comments link should indicate the new comment
        comments_link = tab.find_element_by_xpath('//div[@class="task-comments"]'
                '/div/a[@class="comments-link"]').text
        self.assertEqual(comments_link, '1')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1396874
    def test_virt_doesnt_show_OS_link_after_reservation_complete(self):
        with session.begin():
            start_time = datetime.datetime.utcnow()
            finish_time = start_time + datetime.timedelta(hours=1)
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_complete(recipe, virt=True, start_time=start_time, finish_time=finish_time)

        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        summary_without_link_xpath = '//div[@class="recipe-summary"][not(//a[contains(., "OpenStack instance %s")])]' % (recipe.resource.instance_id)
        b.find_element_by_xpath(summary_without_link_xpath)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1396874
    def test_virt_shows_OS_link_during_installation(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe, virt=True)

        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        summary_link = '//div[@class="recipe-summary"]/p/a[contains(., "%s")]' % (recipe.resource.instance_id)
        b.find_element_by_xpath(summary_link)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1396851
    def test_virt_shows_ip_address_if_the_fqdn_can_not_be_resolved(self):
        with session.begin():
            start_time = datetime.datetime.utcnow()
            finish_time = start_time + datetime.timedelta(hours=1)
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_complete(recipe, virt=True)
            recipe.resource.fqdn = 'invalid.openstacklocal'
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Tasks')
        b.find_element_by_xpath('//div[@class="recipe-summary"]'
                '/p[contains(., "%s")]' % recipe.resource.floating_ip)

class TestRecipeViewInstallationTab(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_shows_installation_in_progress(self):
        # When the status is Installing, the Installation tab should say that 
        # it's installing. Sounds obvious, I know, but until Beaker 23 it was 
        # Running instead so it didn't actually work this way...
        with session.begin():
            recipe = data_setup.create_recipe(
                    distro_name=u'PurpleUmbrellaLinux5.11-20160428',
                    variant=u'Server', arch=u'x86_64')
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        summary = tab.find_element_by_xpath(
                './/div[@class="recipe-installation-summary"]/div[1]').text
        self.assertEqual(summary.strip(),
                'Installing PurpleUmbrellaLinux5.11-20160428 Server x86_64.')
        status = tab.find_element_by_xpath(
                './/div[@class="recipe-installation-status"]').text
        self.assertEqual(status.strip(), 'Installing')

    def test_recipe_start_time_is_displayed_as_positive_zero(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        rebooted_timestamp = tab.find_element_by_xpath(
                './/div[@class="recipe-installation-progress"]/table'
                '//td[contains(string(following-sibling::td), "System rebooted")]').text
        self.assertEqual(rebooted_timestamp, '+00:00:00')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1362370
    def test_configure_netboot_progress_is_not_shown_unless_command_is_complete(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe,
                    lab_controller=data_setup.create_labcontroller())
            recipe.provision()
            configure_netboot_cmd = recipe.installation.commands[1]
            self.assertEquals(configure_netboot_cmd.action, u'configure_netboot')
            self.assertEquals(configure_netboot_cmd.status, CommandStatus.queued)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        tab.find_element_by_xpath(
                './/div[@class="recipe-installation-progress" and '
                'text()="No installation progress reported."]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1318524
    def test_configure_netboot_progress_shows_command_finish_time(self):
        # We want to show the timestamp at which beaker-provision finished 
        # actually running the configure_netboot command, not the time at which 
        # we enqueued the command.
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe,
                    start_time=datetime.datetime(2016, 9, 7, 15, 5, 59))
            configure_netboot_cmd = recipe.installation.commands[1]
            self.assertEquals(configure_netboot_cmd.action, u'configure_netboot')
            configure_netboot_cmd.finish_time = datetime.datetime(2016, 9, 7, 15, 5, 0)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        netboot_configured_timestamp = tab.find_element_by_xpath(
                './/div[@class="recipe-installation-progress"]/table'
                '//td[contains(string(following-sibling::td), "Netboot configured")]').text
        self.assertEqual(netboot_configured_timestamp, '-00:00:59')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1361961
    def test_create_openstack_instance_progress_is_shown(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_installing(recipe, virt=True)
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Installation')
        tab = b.find_element_by_id('installation')
        openstack_instance_progress = tab.find_element_by_xpath(
                './/div[@class="recipe-installation-progress"]/table'
                '//td[contains(text(), "OpenStack instance created")]').text
        self.assertIn(recipe.installation.kernel_options, openstack_instance_progress)

class TestRecipeViewReservationTab(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe(reservesys=True)
            self.job = data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_job_running(self.job)
        self.browser = self.get_browser()

    def test_anonymous_cannot_edit_reservation(self):
        b = self.browser
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        b.find_element_by_xpath('//div[@id="reservation" and '
                'not(.//button[normalize-space(string(.))="Edit"])]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1327020
    def test_reservation_form_converts_unit_from_minutes(self):
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="Yes"]').click()
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('5')
        modal.find_element_by_xpath('.//button[text()="Minutes"]').click()
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.reservation_request.duration, 300)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1327020
    def test_reservation_form_converts_unit_from_hours(self):
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="Yes"]').click()
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('1')
        modal.find_element_by_xpath('.//button[text()="Hours"]').click()
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.reservation_request.duration, 3600)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1327020
    def test_reservation_input_sets_html5_maximum_attribute_for_validation(self):
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="Yes"]').click()
        modal.find_element_by_xpath('.//button[text()="Hours"]').click()
        self.assertEqual(
            u'99', b.find_element_by_css_selector('input:invalid').get_attribute('max'))

        modal.find_element_by_xpath('.//button[text()="Minutes"]').click()
        self.assertEqual(
            u'5940', b.find_element_by_css_selector('input:invalid').get_attribute('max'))

    def test_authenticated_user_can_request_reservation(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_job_running(job)
        b = self.browser
        login(b)
        go_to_recipe_view(b, recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="Yes"]').click()
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('300')
        modal.find_element_by_xpath('.//input[@name="when" and @value="onfail"]').click()
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        self.assertEqual(tab.find_element_by_xpath('div/p').text,
                'The system will be reserved for 00:05:00 at the end of the recipe '
                'if the status is Aborted or the result is Fail.')
        with session.begin():
            session.expire_all()
            self.assertEqual(recipe.reservation_request.duration, 300)
            self.assertEqual(recipe.reservation_request.when,
                    RecipeReservationCondition.onfail)

    def test_authenticated_user_can_edit_reservation(self):
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Edit")]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('300')
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.reservation_request.duration, 300)

    def test_anonymous_cannot_extend_or_return_reservation(self):
        b = self.browser
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        #No extend button
        b.find_element_by_xpath('//div[@id="reservation" and '
                'not(.//button[normalize-space(string(.))="Extend the reservation"])]')

        #No return button
        b.find_element_by_xpath('//div[@id="reservation" and '
                'not(.//button[normalize-space(string(.))="Return the reservation"])]')

    def test_authenticated_user_can_extend_reservation(self):
        with session.begin():
            data_setup.mark_recipe_tasks_finished(self.recipe, only=True)
            self.job.update_status()
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Extend the reservation")]')\
                .click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('600')
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1358619
    def test_recipe_reservation_extension_causes_immediate_watchdog_time_change(self):
        with session.begin():
            data_setup.mark_recipe_tasks_finished(self.recipe, only=True)
            self.job.update_status()
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')

        # Edit the reservation extension to be 10 mins
        tab.find_element_by_xpath('.//button[contains(text(), "Extend the reservation")]')\
                .click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('599')

        # close the modal
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')

        # check watchdog timer has been updated
        new_duration = b.find_element_by_class_name('recipe-watchdog-time-remaining').text
        self.assertRegexpMatches(new_duration, r'00:09:\d\d')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1358619
    def test_extend_reservation_modal_shows_accurate_time_remaining(self):
        with session.begin():
            data_setup.mark_recipe_tasks_finished(self.recipe, only=True)
            self.job.update_status()
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')

        # Edit the reservation extension to be 10 mins
        tab.find_element_by_xpath('.//button[contains(text(), "Extend the reservation")]')\
                .click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_name('reserve_duration').clear()
        modal.find_element_by_name('reserve_duration').send_keys('600')

        # close the modal
        modal.find_element_by_xpath('.//button[text()="Save changes"]').click()
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')

        # wait 1 second
        time.sleep(1)

        # open the modal
        tab.find_element_by_xpath('.//button[contains(text(), "Extend the reservation")]')\
                .click()
        modal = b.find_element_by_class_name('modal')
        self.assertNotEquals(modal.find_element_by_id('reserve_duration').get_attribute('value'), '600')

    def test_authenticated_user_can_return_reservation(self):
        with session.begin():
            data_setup.mark_recipe_tasks_finished(self.recipe, only=True)
            self.job.update_status()
        b = self.browser
        login(b)
        go_to_recipe_view(b, self.recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        tab.find_element_by_xpath('.//button[contains(text(), "Return the reservation")]')\
                .click()
        # Button goes to "Returning..." and confirmation modal appears
        tab.find_element_by_xpath(u'.//button[normalize-space(string(.))="Returning\u2026"]')
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        # Modal disappears, but the request is still going...
        b.find_element_by_xpath('//body[not(.//div[contains(@class, "modal")])]')
        # The "Returning..." button disappears when the request is complete
        tab.find_element_by_xpath(u'//body[not(.//button[normalize-space(string(.))='
                '"Returning\u2026"])]')
        with session.begin():
            session.expire_all()
            self.assertLessEqual(self.recipe.status_watchdog(), 0)

    def test_shows_other_recipes_in_recipeset_holding_this_reservation(self):
        # Beaker keeps all systems in a recipe set reserved until all recipes 
        # in the set are finished. This is to allow for things like multi-host 
        # tests and virt testing, where one recipe might "drop off the end" but 
        # the other machines still want to talk to it.
        # This is a frequent gotcha for users ("why is this system still 
        # reserved even though the recipe is finished?") so we went to some 
        # lengths in the new recipe page to indicate when this happens.
        with session.begin():
            job = data_setup.create_job(num_recipes=2, num_guestrecipes=1)
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_complete(recipe)
            data_setup.mark_recipe_running(job.recipesets[0].recipes[1])
        b = self.browser
        go_to_recipe_view(b, recipe, tab='Reservation')
        tab = b.find_element_by_id('reservation')
        self.assertEqual(tab.find_element_by_xpath('div/p[2]').text,
                'However, the system has not been released yet because '
                'the following recipes are still running:')
        running_recipes_list_items = [li.text for li in
                tab.find_elements_by_xpath('.//ul[@class="running-recipes-list"]/li')]
        self.assertEqual(running_recipes_list_items,
                [job.recipesets[0].recipes[1].t_id,
                 job.recipesets[0].recipes[2].t_id])

class RecipeHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for recipes.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password='theowner')
            self.recipe = data_setup.create_recipe()
            self.recipe_with_reservation_request = data_setup.create_recipe(reservesys=True)
            self.recipe_without_reservation_request = data_setup.create_recipe()
            self.job = data_setup.create_job_for_recipes([
                    self.recipe,
                    self.recipe_with_reservation_request,
                    self.recipe_without_reservation_request],
                    owner=self.owner)

    def test_get_recipe(self):
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['t_id'], self.recipe.t_id)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1361002
    def test_get_virt_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe, virt=True)
        response = requests.get(get_server_base() +
                'recipes/%s' % recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        json = response.json()
        self.assertEquals(json['resource']['instance_id'],
                unicode(recipe.resource.instance_id))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1324305
    def test_get_scheduled_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_scheduled(recipe)
            self.assertIsNone(recipe.watchdog.kill_time)
        response = requests.get(get_server_base() +
                'recipes/%s' % recipe.id,
                headers={'Accept': 'application/json'})
        json = response.json()
        self.assertEquals(json['t_id'], recipe.t_id)
        # time_remaining_seconds should be None as the recipe sits in Scheduled
        # with no watchdog kill time.
        self.assertIsNone(json['time_remaining_seconds'])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1324401
    def test_set_vary_header(self):
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertIn('Vary', response.headers)

    def test_get_recipe_xml(self):
        response = requests.get(get_server_base() + 'recipes/%s.xml' % self.recipe.id)
        response.raise_for_status()
        self.assertEquals(response.status_code, 200)
        self.assertEquals(
                lxml.etree.tostring(self.recipe.to_xml(), pretty_print=True, encoding='utf8'),
                response.content)

    # https://bugzilla.redhat.com/show_bug.cgi?id=915319#c6
    def test_get_recipe_xml_without_logs(self):
        response = requests.get(get_server_base() + 'recipes/%s.xml?include_logs=false' % self.recipe.id)
        response.raise_for_status()
        self.assertNotIn('<log', response.content)

    def test_get_junit_xml(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        response = requests.get(get_server_base() + 'recipes/%s.junit.xml' % self.recipe.id)
        response.raise_for_status()
        self.assertEquals(response.status_code, 200)
        junitxml = lxml.etree.fromstring(response.content)
        self.assertEqual(junitxml.tag, 'testsuites')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1169838
    def test_trailing_slash_should_return_404(self):
        response = requests.get(get_server_base() + 'recipes/%s/' % self.recipe.id)
        self.assertEqual(response.status_code, 404)

    def test_get_recipe_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/recipe_path/dummy.txt' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/beaker/recipe_path/dummy.txt')

    def test_404_for_nonexistent_log(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
        response = requests.get(get_server_base() +
                'recipes/%s/logs/doesnotexist.log' % recipe.id,
                allow_redirects=False)
        self.assertEqual(response.status_code, 404)
        self.assertRegexpMatches(response.text, 'Recipe log .* not found')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1622805
    def test_redirects_beah_log_to_restraint(self):
        with session.begin():
            job = data_setup.create_completed_job(server_log=True)
            recipe = job.recipesets[0].recipes[0]
            rt = recipe.tasks[0]
            rt.logs = [LogRecipeTask(server=u'http://dummy-archive-server/',
                                     filename=u'taskout.log')]
        # Client is looking for TESTOUT.log (old filename from Beah)
        # but the task only has taskout.log (new filename from Restraint)
        # so we expect to be redirected to that.
        response = requests.get(get_server_base() +
                'recipes/%s/tasks/%s/logs/TESTOUT.log' % (recipe.id, rt.id),
                allow_redirects=False)
        self.assertEqual(response.status_code, 307)
        self.assertEqual(response.headers['Location'],
                'http://dummy-archive-server/taskout.log')

    def test_anonymous_cannot_update_recipe(self):
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                data={'whiteboard': u'testwhiteboard'})
        self.assertEquals(response.status_code, 401)

    def test_can_update_recipe_whiteboard(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s' % self.recipe.id,
                session=s, data={'whiteboard': u'newwhiteboard'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe.whiteboard, 'newwhiteboard')
            self.assertEquals(self.recipe.activity[0].field_name, u'Whiteboard')
            self.assertEquals(self.recipe.activity[0].action, u'Changed')
            self.assertEquals(self.recipe.activity[0].new_value, u'newwhiteboard')

    def test_anonymous_cannot_update_reservation_request(self):
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                data={'reserve': True, 'duration': 300})
        self.assertEquals(response.status_code, 401)

    def test_cannot_update_reservation_request_on_completed_recipe(self):
        with session.begin():
            data_setup.mark_job_complete(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': False})
        self.assertEquals(response.status_code, 403)

    def test_cannot_update_reservation_request_if_duration_too_long(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 605000})
        self.assertEquals(response.status_code, 400)

    def test_can_update_reservation_request_to_reserve_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        # On a recipe with reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300, 'when': 'onfail'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEquals(self.recipe_with_reservation_request.reservation_request.when,
                    RecipeReservationCondition.onfail)
            self.assertEquals(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Condition')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].new_value,
                    u'onfail')
            self.assertEquals(self.recipe_with_reservation_request.reservation_request.duration,
                    300)
            self.assertEquals(self.recipe_with_reservation_request.activity[1].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_with_reservation_request.activity[1].action,
                    u'Changed')
            self.assertEquals(self.recipe_with_reservation_request.activity[1].new_value,
                    u'300')
        # On a recipe without reservation request
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_without_reservation_request.id,
                session=s, data={'reserve': True, 'duration': 300, 'when': 'onfail'})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertTrue(self.recipe_without_reservation_request.reservation_request)
            self.assertEquals(self.recipe_without_reservation_request.reservation_request.when,
                    RecipeReservationCondition.onfail)
            self.assertEquals(self.recipe_without_reservation_request.activity[0].field_name,
                    u'Reservation Condition')
            self.assertEquals(self.recipe_without_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_without_reservation_request.activity[0].new_value,
                    u'onfail')
            self.assertEquals(self.recipe_without_reservation_request.reservation_request.duration,
                    300)
            self.assertEquals(self.recipe_without_reservation_request.activity[1].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_without_reservation_request.activity[1].action,
                    u'Changed')
            self.assertEquals(self.recipe_without_reservation_request.activity[1].new_value,
                    u'300')

    def test_can_update_reservation_request_to_not_reserve_the_system(self):
        with session.begin():
            data_setup.mark_job_running(self.job)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': False})
        response.raise_for_status()

        with session.begin():
            session.expire_all()
            self.assertFalse(self.recipe_with_reservation_request.reservation_request)
            self.assertEquals(self.recipe_with_reservation_request.activity[0].field_name,
                    u'Reservation Request')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].action,
                    u'Changed')
            self.assertEquals(self.recipe_with_reservation_request.activity[0].new_value,
                    None)

    def test_rejects_unrecognised_reserve_conditions(self):
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() +
                'recipes/%s/reservation-request' % self.recipe_with_reservation_request.id,
                session=s, data={'reserve': True, 'when': 'slartibartfast'})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.text,
                "Invalid value for RecipeReservationCondition: "
                "u'slartibartfast' is not one of onabort, onfail, onwarn, always")

    def test_anonymous_has_no_reviewed_state(self):
        # Reviewed state is per-user so anonymous should get "reviewed": null 
        # (neither true nor false, since we don't know).
        response = requests.get(get_server_base() +
                'recipes/%s' % self.recipe.id,
                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(response.json()['reviewed'], None)

    def test_can_clear_reviewed_state(self):
        with session.begin():
            self.recipe.set_reviewed_state(self.owner, True)
        s = requests.Session()
        requests_login(s, user=self.owner, password=u'theowner')
        response = patch_json(get_server_base() + 'recipes/%s' % self.recipe.id,
                session=s, data={'reviewed': False})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.recipe.get_reviewed_state(self.owner), False)
