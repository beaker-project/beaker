import unittest
from turbogears.database import session
from bkr.server.model import Activity, Group
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
        with session.begin():
            self.assertEquals(Activity.query.filter_by(service=u'XMLRPC',
                    field_name=u'Group', action=u'Added',
                    new_value=display_name).count(), 1)
            group = Group.by_name(group_name)
            self.assertEquals(group.display_name, display_name)
            self.assertEquals(group.activity[-1].action, u'Added')
            self.assertEquals(group.activity[-1].field_name, u'Owner')
            self.assertEquals(group.activity[-1].new_value, data_setup.ADMIN_USER)
            self.assertEquals(group.activity[-1].service, u'XMLRPC')
            self.assertEquals(group.activity[-2].action, u'Added')
            self.assertEquals(group.activity[-2].field_name, u'User')
            self.assertEquals(group.activity[-2].new_value, data_setup.ADMIN_USER)
            self.assertEquals(group.activity[-2].service, u'XMLRPC')

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
