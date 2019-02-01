
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.server.model import LabController
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

class LabControllerModifyTest(ClientTestCase):

    def test_change_fqdn(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            data_setup.create_labcontroller()
        new_fqdn = data_setup.unique_name(u'lab%s.testdata.invalid')
        run_client(['bkr', 'labcontroller-modify',
                    '--fqdn', new_fqdn,
                    lc.fqdn])
        with session.begin():
            session.refresh(lc)
            self.assertEquals(lc.fqdn, new_fqdn)

    def test_change_fqdn_being_used_by_another_lab_controller(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            another_lc = data_setup.create_labcontroller()
        data_setup.unique_name(u'lab%s.testdata.invalid')
        try:
            run_client(['bkr', 'labcontroller-modify',
                        '--fqdn', another_lc.fqdn,
                        lc.fqdn])
            self.fail('Must error out')
        except ClientError as e:
            self.assertIn('FQDN %s already in use' % another_lc.fqdn,
                          e.stderr_output)

    def test_change_user_name(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            user = data_setup.create_user()
        run_client(['bkr', 'labcontroller-modify',
                    '--user', user.user_name,
                    lc.fqdn])
        with session.begin():
            session.expire_all()
            self.assertEqual(lc.user.user_name, user.user_name)

    def test_change_password(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
        run_client(['bkr', 'labcontroller-modify',
                    '--password', u'newpassword',
                    lc.fqdn])
        with session.begin():
            session.expire_all()
            self.assertTrue(lc.user.check_password(u'newpassword'))

    def test_change_email_address(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            user = data_setup.create_user()
        run_client(['bkr', 'labcontroller-modify',
                    '--email', u'newaddress@beaker-project.com',
                    lc.fqdn])
        with session.begin():
            session.expire_all()
            self.assertEqual(lc.user.email_address, u'newaddress@beaker-project.com')

    def test_enable_the_lab_controller(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            lc.disabled = True
            user = data_setup.create_user()
        run_client(['bkr', 'labcontroller-modify',
                    '--enable',
                    lc.fqdn])
        with session.begin():
            session.expire_all()
            self.assertFalse(lc.disabled)

    def test_disable_the_lab_controller(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            user = data_setup.create_user()
        run_client(['bkr', 'labcontroller-modify',
                    '--disable',
                    lc.fqdn])
        with session.begin():
            session.expire_all()
            self.assertTrue(lc.disabled)

    def test_create_the_lab_controller_if_it_does_not_exist(self):
        with session.begin():
            fqdn = data_setup.unique_name(u'lc%s.com')
            user = data_setup.create_user()
        run_client(['bkr', 'labcontroller-modify',
                    '--user', user.user_name,
                    '--create', fqdn])
        with session.begin():
            lc = LabController.query.filter_by(fqdn=fqdn).one()
            self.assertEqual(lc.user, user)

    def test_create_option_is_ignored_if_the_lab_controller_alreay_exists(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            user = data_setup.create_user()
            self.assertNotEqual(lc.user.user_name, user.user_name)
        run_client(['bkr', 'labcontroller-modify',
                    '--user', user.user_name,
                    '--create', lc.fqdn])
        with session.begin():
            session.expire_all()
            # the --create option should be ignored and the username of the
            # lab controller's user account should be updated.
            self.assertEqual(lc.user.user_name, user.user_name)
