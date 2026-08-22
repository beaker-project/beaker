
# vim: set fileencoding=utf-8:

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests
from six.moves import range
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.server.database import session
from bkr.server.model import SystemStatus

class SystemStatusHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface used by bkr system-status.
    """

    def test_it(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=data_setup.create_labcontroller(),
                                              status=SystemStatus.manual)
            reserved_by = data_setup.create_user(u'dracula')
            loaned_to = data_setup.create_user(u'wolfman')
            system.reserve_manually(user=reserved_by, service=u'testdata')
            system.loaned = loaned_to
            system.loan_comment = u'For evil purposes'
        response = requests.get(get_server_base() + 'systems/%s/status' % system.fqdn)
        response.raise_for_status()
        json = response.json()
        self.assertEqual(json['condition'], 'Manual')
        reservation_info = json['current_reservation']
        self.assertEqual(reservation_info['user_name'], u'dracula') # Beaker 0.15.3
        self.assertEqual(reservation_info['user']['user_name'], 'dracula') # Beaker 19
        loan_info = json['current_loan']
        self.assertEqual(loan_info['recipient'], u'wolfman') # Beaker 0.15.3
        self.assertEqual(loan_info['recipient_user']['user_name'], 'wolfman') # Beaker 19
        self.assertEqual(loan_info['comment'], u'For evil purposes')

class SystemActivityHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for system activity.
    """

    # https://bugzilla.redhat.com/show_bug.cgi?id=1193746
    def test_enforced_pagination_redirect(self):
        with session.begin():
            system = data_setup.create_system()
            # need >500 activity rows to trigger forced pagination
            for _ in range(501):
                system.record_activity(service=u'testdata',
                        field=u'nonsense', action=u'poke')
        original_url = (get_server_base() +
                'systems/%s/activity/?q=action:poke' % system.fqdn)
        expected_redirect = (get_server_base() +
                'systems/%s/activity/?q=action:poke&page_size=20' % system.fqdn)
        response = requests.get(original_url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], expected_redirect)
        # For completeness, the same thing with no query params.
        original_url = (get_server_base() +
                'systems/%s/activity/' % system.fqdn)
        expected_redirect = (get_server_base() +
                'systems/%s/activity/?page_size=20' % system.fqdn)
        response = requests.get(original_url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], expected_redirect)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1401964
    def test_filter_by_activity_id_range(self):
        with session.begin():
            system = data_setup.create_system()
            excluded_activity = system.record_activity(service=u'testdata',
                    field=u'nonsense', action=u'fire')
            included_activity = system.record_activity(service=u'testdata',
                    field=u'nonsense', action=u'fire')
        url = (get_server_base() +
                'systems/%s/activity/?q=id:[%s TO *]' %
                (system.fqdn, included_activity.id))
        response = requests.get(url, allow_redirects=False,
                headers={'Accept': 'application/json'})
        results = [activity['id'] for activity in response.json()['entries']]
        self.assertIn(included_activity.id, results)
        self.assertNotIn(excluded_activity.id, results)
