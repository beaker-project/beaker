
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login
from bkr.inttest import data_setup, get_server_base
from turbogears.database import session

# OLD, DEPRECATED JOB PAGE ONLY

class TestProduct(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()
        with session.begin():
            self.user = data_setup.create_user(password=u'password')
            self.user.use_old_job_page = True

    def test_product_ordering(self):
        with session.begin():
            job = data_setup.create_job()
            product_before = data_setup.create_product()
            product_after = data_setup.create_product()
        b = self.browser
        login(b, user=self.user.user_name, password='password')
        b.get(get_server_base() + 'jobs/%s' % job.id)
        product_select = b.find_element_by_xpath('//select[@id="job_product"]')
        options = [option.text for option in
                product_select.find_elements_by_tag_name('option')]
        before_pos = options.index(product_before.name)
        after_pos = options.index(product_after.name)
        self.assertLess(before_pos, after_pos)
