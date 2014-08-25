
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from selenium.webdriver.support.ui import Select
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base

class RetentionTagTest(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_edit(self):
        with session.begin():
            tag = data_setup.create_retention_tag()
            tag.expire_in_days = 30
            tag.needs_product = True
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text(tag.tag).click()
        b.find_element_by_name('expire_in_days').clear()
        b.find_element_by_name('expire_in_days').send_keys('60')
        self.assertTrue(b.find_element_by_name('needs_product').is_selected())
        b.find_element_by_name('needs_product').click()
        b.find_element_by_id('Retention Tag').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        with session.begin():
            session.refresh(tag)
            self.assertEquals(tag.expire_in_days, 60)
            self.assertEquals(tag.needs_product, False)

    def test_rename(self):
        with session.begin():
            tag = data_setup.create_retention_tag()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text(tag.tag).click()
        b.find_element_by_name('tag').clear()
        b.find_element_by_name('tag').send_keys('pink-fluffy-unicorns')
        b.find_element_by_id('Retention Tag').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        with session.begin():
            session.refresh(tag)
            self.assertEquals(tag.tag, u'pink-fluffy-unicorns')

    def test_cannot_change_tag_name_to_an_existing_tag(self):
        with session.begin():
            existing_tag = data_setup.create_retention_tag()
            tag_to_edit = data_setup.create_retention_tag()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text(tag_to_edit.tag).click()
        b.find_element_by_name('tag').clear()
        b.find_element_by_name('tag').send_keys(existing_tag.tag)
        b.find_element_by_id('Retention Tag').submit()
        b.find_element_by_xpath('//div[@class="control-group error" and .//input[@name="tag"]]'
                '//span[string(.)="Retention tag already exists"]')

    def test_tag_delete(self):
        with session.begin():
            default_tag = data_setup.create_retention_tag(default=True)
            tag_with_job = data_setup.create_retention_tag(default=False)
            new_job = data_setup.create_job()
            new_job.retention_tag = tag_with_job
            non_default_tag = data_setup.create_retention_tag(default=False)
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/delete/%s' % default_tag.id)
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s is not applicable for deletion' % default_tag.tag)

        b.get(get_server_base() + 'retentiontag/delete/%s' % tag_with_job.id)
        self.assertEquals(b.find_element_by_class_name('flash').text,
                '%s is not applicable for deletion' % tag_with_job.tag)

        b.get(get_server_base() + 'retentiontag/delete/%s' % non_default_tag.id)
        self.assertEquals(b.find_element_by_class_name('flash').text,
                'Successfully deleted %s' % non_default_tag.tag)

    def test_tag_add(self):
        b = self.browser
        login(b)
        tag_to_add = 'foo'
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('tag').send_keys(tag_to_add)
        Select(b.find_element_by_name('default')).select_by_visible_text('True')
        b.find_element_by_name('needs_product').click()
        b.find_element_by_id('Retention Tag').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        b.find_element_by_xpath(
                '//table/tbody/tr/td[1][normalize-space(string(.))="%s"]' % tag_to_add)

        tag_to_add = 'bar'
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('tag').send_keys(tag_to_add)
        Select(b.find_element_by_name('default')).select_by_visible_text('False')
        b.find_element_by_id('Retention Tag').submit()
        self.assertEquals(b.find_element_by_class_name('flash').text, 'OK')
        b.find_element_by_link_text(tag_to_add).click()
        self.assertFalse(b.find_element_by_name('needs_product').is_selected())

    def test_add_duplicate_tag(self):
        with session.begin():
            existing_tag = data_setup.create_retention_tag()
        b = self.browser
        login(b)
        b.get(get_server_base() + 'retentiontag/admin')
        b.find_element_by_link_text('Add').click()
        b.find_element_by_name('tag').send_keys(existing_tag.tag)
        Select(b.find_element_by_name('default')).select_by_visible_text('False')
        b.find_element_by_id('Retention Tag').submit()
        b.find_element_by_xpath('//div[@class="control-group error" and .//input[@name="tag"]]'
                '//span[string(.)="Retention tag already exists"]')
