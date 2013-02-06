import unittest
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class WatchdogsExtend(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=906803
    def test_watchdogs_extend(self):

        # As the default admin user
        out = run_client(['bkr', 'watchdogs-extend'])
        self.assert_(out.rstrip('\n') == 'No active watchdogs found' \
                        or 'watchdog moved from' in out)

        # As a non-admin user
        user1 = data_setup.create_user(password='abc')
        try:
            out = run_client(['bkr', 'watchdogs-extend',\
                                  '--username',user1.user_name,'--password','abc'])
        except ClientError, e:
            self.assert_('Not member of group: admin' in e.stderr_output)
