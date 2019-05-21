
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import contextlib
from turbogears.database import session
from bkr.server.model import SystemPermission
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client, create_client_config, ClientError, \
        ClientTestCase

class SystemLoanTest(ClientTestCase):
    # This test checks the loan management CLI is wired up correctly
    # It doesn't check all the access policy variations, since that's
    # covered by the access policy unit tests - these tests are just about
    # ensuring that user permissions *are* being checked

    @with_transaction
    def setUp(self):
        self.user = data_setup.create_user(password=u'asdf')
        self.user2 = data_setup.create_user(password=u'qwerty')

        self.system = data_setup.create_system(owner=self.user,
                lab_controller=data_setup.create_labcontroller())

        self.client_config = create_client_config(
                username=self.user.user_name, password='asdf')
        self.client_config2 = create_client_config(
                username=self.user2.user_name, password='qwerty')
        self.admin_config = create_client_config()

    def assertLoanedTo(self, user, comment=None):
        """Helper to check a suitable loan exists"""
        with session.begin():
            session.refresh(self.system)
            self.assertEqual(self.system.loaned.user_name, user.user_name)
            self.assertEqual(self.system.loan_comment, comment)

    def assertNotLoaned(self):
        """Helper to check the system is not loaned to anyone"""
        with session.begin():
            session.refresh(self.system)
            self.assertIsNone(self.system.loaned)
            self.assertIsNone(self.system.loan_comment)


    @contextlib.contextmanager
    def assertTriggersPermissionsError(self, details):
        """Helper to check correct enforcement of user permissions"""
        expected_error = "Insufficient permissions: %s" % details
        try:
            yield
            self.fail('Permissions error expected')
        except ClientError as e:
            self.assertEqual(e.status, 1)
            self.assertRegexpMatches(e.stderr_output, expected_error)

    def test_owner_can_borrow_system(self):
        # user1 should be able to lend the system to themselves
        out = run_client(['bkr', 'loan-grant', self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Borrowed %s' % self.system.fqdn, out)
        self.assertLoanedTo(self.user)

        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        self.assertNotLoaned()

    def test_loan_comment(self):
        # Set a comment while granting the loan
        out = run_client(['bkr', 'loan-grant',
                          '--comment', 'Mine! All mine!',
                          self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Borrowed %s' % self.system.fqdn, out)
        self.assertLoanedTo(self.user, "Mine! All mine!")

        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        with session.begin():
            session.refresh(self.system)
            self.assertIsNone(self.system.loaned)
            self.assertIsNone(self.system.loan_comment)

    def test_owner_can_lend_system(self):
        # user1 should be able to lend the system to user2
        out = run_client(['bkr', 'loan-grant',
                          '--recipient', self.user2.user_name,
                          self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Loaned %s to %s' %
                                    (self.system.fqdn, self.user2.user_name),
                                 out)
        self.assertLoanedTo(self.user2)
        # user2 still isn't allowed to modify the loan
        details = "%s cannot borrow this system" % self.user2.user_name
        with self.assertTriggersPermissionsError(details):
            out = run_client(['bkr', 'loan-grant',
                            '--comment', 'Mine! All mine!',
                            self.system.fqdn],
                    config=self.client_config2)
        self.assertLoanedTo(self.user2)
        # However, user2 should now be able to return it
        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.client_config2)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        self.assertNotLoaned()

    def test_owner_can_replace_existing_loan(self):
        # First lend the system to user2
        out = run_client(['bkr', 'loan-grant',
                          '--recipient', self.user2.user_name,
                          self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Loaned %s to %s' %
                                    (self.system.fqdn, self.user2.user_name),
                                 out)
        self.assertLoanedTo(self.user2)
        # Now claim it for ourselves
        out = run_client(['bkr', 'loan-grant', self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Borrowed %s' % self.system.fqdn, out)
        self.assertLoanedTo(self.user)
        # Return the system
        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.client_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        self.assertNotLoaned()

    def test_admin_can_lend_system(self):
        # admin should be able to lend the system to another user
        out = run_client(['bkr', 'loan-grant',
                          '--recipient', self.user.user_name,
                          self.system.fqdn],
                config=self.admin_config)
        self.assertRegexpMatches('^Loaned %s to %s' %
                                    (self.system.fqdn, self.user2.user_name),
                                 out)
        self.assertLoanedTo(self.user)
        # user2 cannot return a system loaned to someone else
        details = "%s cannot return system loan" % self.user2.user_name
        with self.assertTriggersPermissionsError(details):
            run_client(['bkr', 'loan-return', self.system.fqdn],
                       config=self.client_config2)
        self.assertLoanedTo(self.user)
        # Admin should be able to return it
        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.admin_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        self.assertNotLoaned()

    def test_user_cannot_borrow_system(self):
        # user2 should not be able to lend the system to themselves
        details = "%s cannot borrow this system" % self.user2.user_name
        with self.assertTriggersPermissionsError(details):
            run_client(['bkr', 'loan-grant', self.system.fqdn],
                       config=self.client_config2)
        self.assertNotLoaned()

    def test_user_with_borrow_permissions_only(self):
        # Grant everyone borrow permissions on the system
        with session.begin():
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.loan_self, everybody=True)

        # user2 should now be able to borrow and return the system
        out = run_client(['bkr', 'loan-grant', self.system.fqdn],
                config=self.client_config2)
        self.assertRegexpMatches('^Borrowed %s' % self.system.fqdn, out)
        self.assertLoanedTo(self.user2)

        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                config=self.client_config2)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                out)
        self.assertNotLoaned()
        # user2 should still not be able to lend the system to anyone else
        details = "%s cannot lend this system" % self.user2.user_name
        with self.assertTriggersPermissionsError(details):
            run_client(['bkr', 'loan-grant',
                        '--recipient', self.user.user_name,
                        self.system.fqdn],
                       config=self.client_config2)
        self.assertNotLoaned()


    def test_returning_unloaned_system(self):
        # user2 cannot even try to return an unloaned system
        details = "%s cannot return system loan" % self.user2.user_name
        with self.assertTriggersPermissionsError(details):
            run_client(['bkr', 'loan-return', self.system.fqdn],
                       config=self.client_config2)
        # System owner and admin can always try to return a system
        # XXX(ncoghlan): the fact we currently claim the loan was returned,
        # when there actually wasn't a loan in place at all is a bit weird
        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                         config=self.client_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
        out = run_client(['bkr', 'loan-return', self.system.fqdn],
                         config=self.admin_config)
        self.assertRegexpMatches('^Returned loan for %s' % self.system.fqdn,
                                 out)
