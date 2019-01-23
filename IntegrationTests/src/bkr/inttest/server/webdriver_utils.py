
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from __future__ import absolute_import

import json
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium import webdriver
from bkr.inttest import data_setup, get_server_base

def delete_and_confirm(browser, ancestor_xpath, delete_text='Delete'):
    browser.find_element_by_xpath(ancestor_xpath)\
           .find_element_by_link_text(delete_text)\
           .click()
    browser.find_element_by_xpath("//button[@type='button' and .//text()='Yes']").click()

def login(browser, user=None, password=None):
    if user is None and password is None:
        user = data_setup.ADMIN_USER
        password = data_setup.ADMIN_PASSWORD
    # A lot of tests call login() before actually loading any page.
    if browser.current_url == 'about:blank':
        browser.get(get_server_base())
    browser.find_element_by_link_text('Log in').click()
    browser.find_element_by_name('user_name').click()
    browser.find_element_by_name('user_name').send_keys(user)
    browser.find_element_by_name('password').click()
    browser.find_element_by_name('password').send_keys(password)
    browser.find_element_by_name('login').click()

def logout(browser):
    browser.find_element_by_xpath('//a[normalize-space(text())="Hello"]').click()
    browser.find_element_by_css_selector('.dropdown.open')\
           .find_element_by_link_text('Log out')\
           .click()
    # check we have been logged out
    wait = WebDriverWait(browser, 30)
    wait.until(lambda browser: browser.find_element_by_link_text('Log in'))

def is_text_present(browser, text):
    return bool(browser.find_elements_by_xpath(
            '//*[contains(text(), "%s")]' % text.replace('"', r'\"')))

def search_for_system(browser, system):
    browser.find_element_by_link_text('Show Search Options').click()
    Select(browser.find_element_by_name('systemsearch-0.table'))\
            .select_by_visible_text('System/Name')
    Select(browser.find_element_by_name('systemsearch-0.operation'))\
            .select_by_visible_text('is')
    browser.find_element_by_name('systemsearch-0.value').send_keys(system.fqdn)
    browser.find_element_by_name('systemsearch').submit()

def wait_for_animation(browser, selector):
    """
    Waits until jQuery animations have finished for the given jQuery selector.
    """
    WebDriverWait(browser, 30).until(lambda browser: browser.execute_script(
            'return jQuery(%s).is(":animated")' % json.dumps(selector))
            == False)

def wait_for_ajax_loading(browser, class_name):
    """
    Waits until the ajax loading indicator disappears.
    """
    wait = WebDriverWait(browser, 30)
    wait.until(lambda browser: len(browser.find_elements_by_class_name(
            class_name)) == 0)

def _activity_row_xpath(activity):
    return ('tr/td[1]/a/text()="%s" and tr/td[2]/text()="%s" and '
            'tr/td[5]/text()="%s" and tr/td[6]/text()="%s" and '
            'tr/td[7]/text()="%s" and tr/td[8]/text()="%s"'
            % (activity.user.user_name, activity.service,
               activity.field_name, activity.action,
               activity.old_value, activity.new_value))
def check_activity_search_results(browser, present=[], absent=[]):
    for activity in absent:
        try:
            browser.find_element_by_xpath(
                    '//div[@id="grid"]/table/tbody[not(%s)]'
                    % _activity_row_xpath(activity))
        except NoSuchElementException:
            raise AssertionError('Grid was missing or contained '
                    'activity entry which was expected to be absent: %r'
                    % activity)
    for activity in present:
        try:
            browser.find_element_by_xpath(
                    '//div[@id="grid"]/table/tbody[%s]'
                    % _activity_row_xpath(activity))
        except NoSuchElementException:
            raise AssertionError('Grid was missing or did not contain '
                    'activity entry: %r' % activity)

def check_pool_search_results(browser, present=[], absent=[]):
    for pool in absent:
        try:
            browser.find_element_by_xpath('//div[@id="grid"]/table'
                '/tbody[not(tr/td[1]/a/text()="%s")]' % pool.name)
        except NoSuchElementException:
            raise AssertionError('Grid was missing or contained '
                    'pool which was expected to be absent: %r'
                    % pool)
    for pool in present:
        try:
            browser.find_element_by_xpath('//div[@id="grid"]/table'
                '/tbody[tr/td[1]/a/text()="%s"]' % pool.name)
        except NoSuchElementException:
            raise AssertionError('Grid was missing or did not contain '
                    'pool: %r' % pool)

def check_system_search_results(browser, present=[], absent=[]):
    for system in absent:
        browser.find_element_by_xpath('//table[@id="widget" and '
                'not(.//td[1]/a/text()="%s")]' % system.fqdn)
    for system in present:
        browser.find_element_by_xpath('//table[@id="widget" and '
                './/td[1]/a/text()="%s"]' % system.fqdn)

def check_job_search_results(browser, present=[], absent=[]):
    for job in absent:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    'not(.//td[1]/a/text()="%s")]' % job.t_id)
    for job in present:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    './/td[1]/a/text()="%s"]' % job.t_id)

def check_recipe_search_results(browser, present=[], absent=[]):
    for recipe in absent:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    'not(.//td[1]/a/text()="%s")]' % recipe.t_id)
    for recipe in present:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    './/td[1]/a/text()="%s"]' % recipe.t_id)

def check_distro_search_results(browser, present=[], absent=[]):
    for distro in absent:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    'not(.//td[1]/a/text()="%s")]' % distro.id)
    for distro in present:
        browser.find_element_by_xpath('//table[@id="widget" and '
                    './/td[1]/a/text()="%s"]' % distro.id)

def check_task_search_results(browser, present=[], absent=[]):
    for task in absent:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[not(tr/td[1]/a/text()="%s")]' % task.name)
    for task in present:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[tr/td[1]/a/text()="%s"]' % task.name)

def check_user_search_results(browser, present=[], absent=[]):
    for user in absent:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[not(tr/td[1]/a/text()="%s")]' % user.user_name)
    for user in present:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[tr/td[1]/a/text()="%s"]' % user.user_name)

def check_group_search_results(browser, present=[], absent=[]):
    for group in absent:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[not(tr/td[1]/a/text()="%s")]' % group.group_name)
    for group in present:
        browser.find_element_by_xpath('//table[contains(@class, "table")]/tbody'
                    '[tr/td[1]/a/text()="%s"]' % group.group_name)

def click_menu_item(browser, menu_item, submenu_item):
    browser.find_element_by_link_text(menu_item).click()
    browser.find_element_by_css_selector('.dropdown.open')\
           .find_element_by_link_text(submenu_item)\
           .click()

def check_policy_row_is_dirty(browser, row):
    pane = browser.find_element_by_id('access-policy')
    # Is it better to check for a class or a specific appearance?
    # Not sure, so let's do both for now.
    cell = pane.find_element_by_xpath('.//table/tbody'
            '/tr[contains(@class, "dirty")]'
            '/td[1][normalize-space(string(.))="%s"]' % row)
    assert cell.value_of_css_property('background-color') != 'transparent'

def check_policy_row_is_not_dirty(browser, row):
    pane = browser.find_element_by_id('access-policy')
    cell = pane.find_element_by_xpath('.//table/tbody'
            '/tr[not(contains(@class, "dirty"))]'
            '/td[1][normalize-space(string(.))="%s"]' % row)
    assert cell.value_of_css_property('background-color') == 'transparent'

def check_policy_row_is_absent(browser, row):
    pane = browser.find_element_by_id('access-policy')
    pane.find_element_by_xpath(
            './/table[not(tbody/tr/td[1][normalize-space(string(.))="%s"])]' % row)

def find_policy_checkbox(browser, row, column):
    """
    Returns the <input type="checkbox"/> for the given row and column labels.
    """
    pane = browser.find_element_by_id('access-policy')
    cols = pane.find_elements_by_xpath('.//table/thead/tr[1]/th')
    col_num = [col.text for col in cols].index(column) + 1
    # using * in the xpaths below since it could be td or th
    row_elem = pane.find_element_by_xpath('.//table/tbody/tr[normalize-space(string(.))="%s"]' % row)
    return row_elem.find_element_by_xpath('./*[%d]/input[@type="checkbox"]' % col_num)


class BootstrapSelect(object):
    """
    Like selenium.webdriver.ui.support.Select but for bootstrap-select,
    which uses Bootstrap buttons and drop-downs rather than a real <select/>
    control.
    """

    def __init__(self, select_element):
        # The select will be hidden, the bootstrap-select will be its sibling.
        self.element = select_element.find_element_by_xpath(
                'following-sibling::div[contains(@class, "bootstrap-select")]')

    def select_by_visible_text(self, text):
        self.element.find_element_by_tag_name('button').click()
        self.element.find_element_by_link_text(text).click()

    @property
    def options(self):
        # Need to open the menu in order to grab the options -- I think this is
        # due to Webdriver hiding "invisible" elements from us
        self.element.find_element_by_tag_name('button').click()
        options = [span.text for span in self.element.find_elements_by_xpath(
                './/ul[contains(@class, "dropdown-menu")]/li//span[@class="text"]')]
        self.element.find_element_by_tag_name('button').click() # close it again
        return options

    @property
    def selected_option_text(self):
        return self.element.find_element_by_tag_name('button').text.strip()
