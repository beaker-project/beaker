
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.model import session, SystemPool
from bkr.inttest import data_setup
from bkr.inttest.client import ClientError, run_client, ClientTestCase
from sqlalchemy.orm.exc import NoResultFound
class DeleteSystemPool(ClientTestCase):

    def test_delete_pool(self):
        with session.begin():
            pool_name = data_setup.unique_name(u'mypool%s')
            data_setup.create_system_pool(name=pool_name)
        run_client(['bkr', 'pool-delete', pool_name])

        with session.begin():
            session.expire_all()
            with self.assertRaises(NoResultFound):
                SystemPool.by_name(pool_name)

        # attempt to delete non-existent pool
        try:
            run_client(['bkr', 'pool-delete', pool_name])
            self.fail()
        except ClientError as e:
            self.assertIn('System pool %s does not exist' % pool_name,
                          e.stderr_output)
