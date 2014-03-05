
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.server.model import Group, User

class RefreshLdapTest(unittest.TestCase):

    def test_refresh_ldap_group_membership(self):
        with session.begin():
            group = Group(group_name=u'alp',
                    display_name=u'Australian Labor Party', ldap=True)
            old_member = data_setup.create_user(user_name=u'krudd')
            group.users.append(old_member)
        from bkr.server.tools.refresh_ldap import refresh_ldap
        refresh_ldap()
        with session.begin():
            session.expire_all()
            self.assertEquals(group.users, [User.by_user_name(u'jgillard')])
        # second time is a no-op
        refresh_ldap()
        with session.begin():
            session.expire_all()
            self.assertEquals(group.users, [User.by_user_name(u'jgillard')])
