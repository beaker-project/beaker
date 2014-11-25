
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
beaker-init is already tested indirectly when the database is populated at the 
start of every test run. In addition, all the database migration code is tested 
by test_database_migration.

So here in this module, we are just testing extra niceties on top of those two 
core functions.
"""

from turbogears.database import session, metadata
from bkr.server.model import User, Group
from bkr.server.tools.init import init_db
from bkr.inttest import data_setup, DatabaseTestCase

class BeakerInitTest(DatabaseTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=745560
    def test_adds_existing_user_to_admin_group(self):
        with session.begin():
            existing_user = data_setup.create_user()
            self.assertEquals(existing_user.groups, [])
        init_db(metadata, user_name=existing_user.user_name)
        with session.begin():
            existing_user = User.query.get(existing_user.user_id)
            admin_group = Group.by_name(u'admin')
            self.assertEquals(existing_user.groups, [admin_group])
