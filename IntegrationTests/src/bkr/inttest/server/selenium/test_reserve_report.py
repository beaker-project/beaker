
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from bkr.server.model import session
from bkr.inttest import data_setup, get_server_base
from bkr.inttest.server.selenium import WebDriverTestCase


class ReserveReportTest(WebDriverTestCase):

    def setUp(self):
        with session.begin():
            user = data_setup.create_user()
            system = data_setup.create_system()
            system.user = user
            data_setup.create_manual_reservation(system,
                                                 datetime.datetime(2012, 10, 31, 23, 0, 0),
                                                 user=user)
        self.browser = self.get_browser()
        self.browser.get(get_server_base() + '/reports')

    def test_report_shows_expected_default_columns(self):
        b = self.browser
        headers = b.find_elements_by_xpath('//div/table[@id="widget"]/thead/tr/th')
        expected = [u'Name',
                    u'LoanedTo',
                    u'Pools',
                    u'Reserved',
                    u'User',
                    ]
        self.assertEqual(expected, [x.text for x in headers])
