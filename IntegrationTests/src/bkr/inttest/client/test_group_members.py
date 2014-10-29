
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase
import json

class GroupMembersTest(ClientTestCase):

    def test_group_members(self):

        with session.begin():
            user2 = data_setup.create_user()
            group = data_setup.create_group(owner=user2)
            user1 = data_setup.create_user()
            user1.groups.append(group)


        # list output
        out = run_client(['bkr', 'group-members',
                          '--format','list',
                          group.group_name])

        self.assert_('%s %s %s' %
                     (user2.user_name, user2.email_address, 'Owner')
                     in out.splitlines(), out.splitlines())
        self.assert_('%s %s %s' %
                     (user1.user_name, user1.email_address, 'Member')
                     in out.splitlines(), out.splitlines())

        # json output
        out = run_client(['bkr', 'group-members',
                          group.group_name])
        out = json.loads(out)
        self.assert_(dict(username=user2.user_name,
                          email=user2.email_address,
                          owner=True) in out, out)
        self.assert_(dict(username=user1.user_name,
                          email=user1.email_address,
                          owner=False) in out, out)

        # non-existent group
        try:
            out = run_client(['bkr', 'group-members',
                              'idontexist'])
            self.fail('Must fail or die')
        except ClientError, e:
            self.assert_('Group does not exist' in
                         e.stderr_output, e.stderr_output)
