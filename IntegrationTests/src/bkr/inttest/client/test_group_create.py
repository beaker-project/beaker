import unittest
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError

class GroupCreateTest(unittest.TestCase):

    def test_group_create(self):
        group_name = data_setup.unique_name('group%s')
        display_name = 'My Group'
        out = run_client(['bkr', 'group-create',
                          '--display-name', display_name,
                          group_name])

        self.assert_('Group created' in out, out)

        group_name = data_setup.unique_name('group%s')
        out = run_client(['bkr', 'group-create',
                          group_name])
        self.assert_('Group created' in out, out)

        group_name = data_setup.unique_name('group%s')

        try:
            out = run_client(['bkr', 'group-create',
                          group_name, group_name])
            self.fail('Must fail or die')
        except ClientError,e:
            self.assert_('Exactly one group name must be specified' in
                         e.stderr_output, e.stderr_output)

    def test_group_duplicate(self):
        group_name = data_setup.unique_name('group%s')
        display_name = 'My Group'
        out = run_client(['bkr', 'group-create',
                          '--display-name',display_name,
                          group_name])

        self.assert_('Group created' in out, out)

        try:
            out = run_client(['bkr', 'group-create',
                              '--display-name',display_name,
                              group_name])
        except ClientError,e:
            self.assert_('Group already exists' in e.stderr_output,
                         e.stderr_output)
