
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import email
import requests
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase, \
        mail_capture_thread
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json
from bkr.server.database import session

class SystemLoanHTTPTest(DatabaseTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1497881
    def test_cannot_lend_to_deleted_user(self):
        with session.begin():
            system = data_setup.create_system()
            deleted_user = data_setup.create_user()
            deleted_user.removed = datetime.datetime.utcnow()
        s = requests.Session()
        requests_login(s)
        response = post_json(get_server_base() + 'systems/%s/loans/' % system.fqdn,
                session=s, data={'recipient': {'user_name': deleted_user.user_name}})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text,
                'Cannot lend to deleted user %s' % deleted_user.user_name)

    # https://bugzilla.redhat.com/show_bug.cgi?id=996165
    def test_sends_mail_notification_for_loan(self):
        with session.begin():
            owner = data_setup.create_user(user_name='mturnbull', email_address='mturnbull@gov.au')
            system = data_setup.create_system(fqdn='lya3.aemo.com.au', owner=owner)
            loanee = data_setup.create_user(user_name='bshorten')
        s = requests.Session()
        requests_login(s)
        mail_capture_thread.start_capturing()
        response = post_json(get_server_base() + 'systems/%s/loans/' % system.fqdn,
                session=s, data={'recipient': {'user_name': 'bshorten'}})
        self.assertEqual(response.status_code, 200)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual(['mturnbull@gov.au'], rcpts)
        self.assertEqual('mturnbull@gov.au', msg['To'])
        self.assertEqual('System lya3.aemo.com.au loaned to bshorten', msg['Subject'])
        self.assertEqual(
                'Beaker system lya3.aemo.com.au <%sview/lya3.aemo.com.au>\n'
                'has been loaned to bshorten by admin.'
                % get_server_base(),
                msg.get_payload(decode=True).decode('utf8'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=996165
    def test_sends_mail_notification_for_loan_return(self):
        with session.begin():
            owner = data_setup.create_user(user_name='mturnbull', email_address='mturnbull@gov.au')
            system = data_setup.create_system(fqdn='lya4.aemo.com.au', owner=owner)
            loanee = data_setup.create_user(user_name='bshorten')
            system.loaned = loanee
        s = requests.Session()
        requests_login(s)
        mail_capture_thread.start_capturing()
        response = patch_json(get_server_base() + 'systems/%s/loans/+current' % system.fqdn,
                session=s, data={'finish': 'now'})
        self.assertEqual(response.status_code, 200)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual(['mturnbull@gov.au'], rcpts)
        self.assertEqual('mturnbull@gov.au', msg['To'])
        self.assertEqual('System lya4.aemo.com.au loan returned', msg['Subject'])
        self.assertEqual(
                'Beaker system lya4.aemo.com.au <%sview/lya4.aemo.com.au>\n'
                'loan has been returned by admin.'
                % get_server_base(),
                msg.get_payload(decode=True).decode('utf8'))
