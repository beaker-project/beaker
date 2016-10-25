
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup, DatabaseTestCase
from bkr.inttest.server.tools import run_command
from bkr.common import __version__
from bkr.server.model import Group, GroupMembershipType, User

class RefreshLdapTest(DatabaseTestCase):

    @classmethod
    def setUpClass(cls):
        # Clear out any LDAP groups left behind by previous tests,
        # to avoid warning spew from beaker-refresh-ldap
        # when it fails to look up the rubbish group names.
        for group in Group.query.filter(Group.membership_type == GroupMembershipType.ldap):
            session.delete(group)

    def test_version(self):
        out = run_command('refresh_ldap.py', 'beaker-refresh-ldap', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_refresh_ldap_group_membership(self):
        with session.begin():
            group = Group(group_name=u'alp',
                    display_name=u'Australian Labor Party',
                    membership_type=GroupMembershipType.ldap)
            old_member = data_setup.create_user(user_name=u'krudd')
            group.add_member(old_member)
        run_command('refresh_ldap.py', 'beaker-refresh-ldap')
        with session.begin():
            session.expire_all()
            self.assertEquals(group.users, [User.by_user_name(u'jgillard')])
        # second time is a no-op
        run_command('refresh_ldap.py', 'beaker-refresh-ldap')
        with session.begin():
            session.expire_all()
            self.assertEquals(group.users, [User.by_user_name(u'jgillard')])
