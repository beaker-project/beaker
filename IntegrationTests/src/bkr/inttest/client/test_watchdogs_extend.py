
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase


class WatchdogsExtend(ClientTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=906803
    def test_watchdogs_extend(self):

        # As the default admin user
        out = run_client(['bkr', 'watchdogs-extend'])
        self.assert_(out.rstrip('\n') == 'No active watchdogs found' \
                        or 'watchdog moved from' in out)

        # As a non-admin user
        with session.begin():
            user1 = data_setup.create_user(password='abc')
        try:
            run_client(['bkr', 'watchdogs-extend',
                        '--username',user1.user_name,'--password','abc'])
        except ClientError as e:
            self.assert_('Not member of group: admin' in e.stderr_output)
