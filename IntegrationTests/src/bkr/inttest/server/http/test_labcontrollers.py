
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import datetime
import requests
from six import assertRegex
from sqlalchemy.orm.exc import NoResultFound

from bkr.server.database import session
from bkr.server.model import LabController, Group
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.inttest.server.requests_utils import login as web_login, post_json, patch_json


class LabControllerHTTPTest(DatabaseTestCase):

    def setUp(self):
        self.lc_fqdn = u'lab.domain.com'
        with session.begin():
            self.lc_user = data_setup.create_admin(password='theowner')
            self.user_password = '_'
            self.user = data_setup.create_user(password=self.user_password)
            self.lc = data_setup.create_labcontroller(fqdn=self.lc_fqdn,
                                                      user=self.lc_user)

    def test_no_labcontroller(self):
        """Not existing lab controller results in a 404."""
        response = requests.get(
            get_server_base() + 'labcontrollers/doesnotexist',
            headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.text.endswith('does not exist'))

    def test_creates_labcontroller_with_new_user(self):
        """Verify that we can create a new lab controller."""
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'user_name': 'mjia',
                'password': '',
                'email_address': 'mjia@beaker-project.org'}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)

        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.json()['id'])
        with session.begin():
            lc = LabController.query.filter_by(fqdn=data['fqdn']).one()
            self.assertEqual(lc.user.user_name, data['user_name'])
            self.assertEqual(lc.user.email_address, data['email_address'])
            self.assertIn(Group.by_name(u'lab_controller'), lc.user.groups)

    def test_creates_labcontroller_with_existing_user(self):
        """Verify that a new lab controller is created with an existing user."""
        with session.begin():
            user_name = 'Frank'
            display_name = 'Beaker Boyz'
            data_setup.create_user(user_name=user_name,
                                   display_name=display_name,
                                   email_address='bbz@beaker-project.org')

        s = requests.Session()
        web_login(s)
        response = post_json(
            get_server_base() + '/labcontrollers/',
            session=s,
            data={'fqdn': 'lc1.beer.newtest',
                  'user_name': user_name,
                  'email_address': 'different@redhat.com',
            })

        self.assertEqual(response.status_code, 201)
        with session.begin():
            session.expire_all()
            lc = LabController.query.filter_by(fqdn='lc1.beer.newtest').one()
            self.assertEqual(lc.user.user_name, user_name)
            # The existing user's display name and email address should be overridden.
            self.assertEqual(lc.user.display_name, lc.fqdn)
            self.assertEqual(lc.user.email_address, 'different@redhat.com' )
            self.assertIn(Group.by_name(u'lab_controller'), lc.user.groups)

    def test_creates_labcontroller_with_existing_labcontroller_user(self):
        """Verifies adding a new lab controller with a user associated to an
        existing lab controller results in an error."""
        s = requests.Session()
        web_login(s)
        data = {'fqdn': 'lc1.beer.newtest',
                'user_name': self.lc.user.user_name}

        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)

        self.assertEqual(response.status_code, 400)
        self.assertTrue(re.search('is already associated with lab controller', response.text))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_with_invalid_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        user_name = data_setup.unique_name('user%s')
        data = {'fqdn': fqdn,
                'user_name': user_name,
                'password': '',
                'email_address': 'asdf'}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid email address', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_with_empty_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        user_name = data_setup.unique_name('user%s')
        data = {'fqdn': fqdn,
                'user_name': user_name,
                'password': '',
                'email_address': ''}
        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1337812
    def test_does_not_create_labcontroller_without_email_address(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'user_name': data_setup.unique_name('user%s')}

        response = post_json(
            get_server_base() + '/labcontrollers/', session=s, data=data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('Email address must not be empty', response.text)

    def test_get_labcontroller_json(self):
        """Can successfully retrieve lab controller details in JSON."""
        response = requests.get(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            headers={'Accept': 'application/json'}
        )
        expected = {
            u'fqdn': self.lc.fqdn,
            u'id': self.lc.id,
            u'disabled': self.lc.disabled,
            u'is_removed': bool(self.lc.removed),
            u'removed': self.lc.removed,
            u'display_name': self.lc.user.display_name,
            u'email_address': self.lc.user.email_address,
            u'user_name': self.lc.user.user_name
        }
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(expected, response.json())

    def test_no_change_with_incorrect_data(self):
        """Lab controllers don't change if different data is passed."""
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'ignored': '_'})
        self.assertEqual(response.status_code, 200)

    def test_no_permission(self):
        """Authorised users with improper permissions can not change the lab
        controller.
        """
        # guard so we can be sure the test does pass because this user got all
        # of a sudden admin rights
        self.assertFalse(self.lc.can_edit(self.user))

        s = requests.Session()
        web_login(s, self.user, password=self.user_password)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 403)
        self.assertTrue(re.search('Cannot edit lab controller', response.text))

    def test_renames_successfully(self):
        """Renames the lab controller successfully."""
        data = {'fqdn': data_setup.unique_name('lc%s.com'),
                'user_name': self.lc.user.user_name,
                'email_address': self.lc.user.email_address}

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn, session=s, data=data)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['fqdn'], data['fqdn'])
        self.assertEqual(get_server_base() + 'labcontrollers/%s' % data['fqdn'],
                         response.headers['Location'])
        with session.begin():
            lc = LabController.by_name(data['fqdn'])
            self.assertRaises(NoResultFound, LabController.by_name, self.lc.fqdn)
            session.refresh(lc.user)
            self.assertEqual(self.lc.user.display_name, data['fqdn'])
            self.assertTrue(lc)

    def test_renames_duplicated_labcontroller_errors(self):
        """Verify that we get a useful error message if we rename to an
        existing lab controller."""
        with session.begin():
            lc = data_setup.create_labcontroller()

        s = requests.Session()
        web_login(s)
        response = patch_json(get_server_base() + 'labcontrollers/' + self.lc.fqdn,
                              session=s,
                              data={'fqdn': lc.fqdn})

        self.assertEqual(response.status_code, 400)
        assertRegex(
            self,
            response.text,
            re.compile(r'FQDN %s already in use' % lc.fqdn)
        )

    def test_disables_labcontroller_successfully(self):
        with session.begin():
            session.refresh(self.lc)
            self.assertFalse(self.lc.disabled)

        s = requests.Session()
        web_login(s)
        response = patch_json(get_server_base() + 'labcontrollers/' + self.lc.fqdn,
                              session=s,
                              data={'disabled': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['disabled'])

        with session.begin():
            session.refresh(self.lc)
            self.assertTrue(self.lc.disabled)
            self.assertEqual(self.lc.activity[0].action, 'Changed')
            self.assertEqual(self.lc.activity[0].field_name, 'disabled')

    def test_changes_user_successfully(self):
        """Changes the lab controller credentials successfully."""
        with session.begin():
            group = Group.by_name('lab_controller')
            self.assertNotIn(group, self.user.groups)

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'user_name': self.user.user_name})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            for obj in [self.lc, self.user, group]:
                session.refresh(obj)

            self.assertDictEqual({
                'id': self.lc.id,
                'fqdn': self.lc.fqdn,
                'disabled': self.lc.disabled,
                'is_removed': bool(self.lc.removed),
                'removed': self.lc.removed,
                'display_name': self.lc.fqdn,
                'email_address': self.user.email_address,
                'user_name': self.user.user_name,
            }, response.json())
            self.assertEqual(self.lc.fqdn, self.user.display_name)
            self.assertIn(group, self.lc.user.groups)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_update_password(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'password': u'newpassword'})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertTrue(self.lc.user.check_password(u'newpassword'))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_update_email_address(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'email_address': u'new_email_address@beaker-project.org'})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertEqual(self.lc.user.email_address, u'new_email_address@beaker-project.org')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1339034
    def test_changes_user_and_fqdn_successfully(self):
        """Changes the lab controller credentials and FQDN at the same time successfully."""
        with session.begin():
            fqdn = data_setup.unique_name('lc%s.com')
            user = data_setup.create_user()
            group = Group.by_name('lab_controller')
            self.assertNotIn(group, user.groups)

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': fqdn,
                  'user_name': user.user_name})
        self.assertEqual(response.status_code, 200)

        with session.begin():
            for obj in [self.lc, user, group]:
                session.refresh(obj)

            self.assertDictEqual({
                'id': self.lc.id,
                'fqdn': fqdn,
                'disabled': self.lc.disabled,
                'is_removed': bool(self.lc.removed),
                'removed': self.lc.removed,
                'display_name': fqdn,
                'email_address': user.email_address,
                'user_name': user.user_name,
            }, response.json())
            self.assertEqual(self.lc.fqdn, user.display_name)
            self.assertIn(group, self.lc.user.groups)

    def test_removed_labcontroller_can_be_restored(self):
        """Verifies that a removed lab controller can be restored."""
        with session.begin():
            self.lc.disabled = True
            self.lc.removed = datetime.datetime.utcnow()

        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + '/labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'removed': False})

        self.assertEqual(response.status_code, 200)

        with session.begin():
            session.expire_all()
            self.assertFalse(self.lc.disabled)
            self.assertIsNone(self.lc.removed)

    def test_update_labcontroller_with_empty_fqdn(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': u''})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Lab controller FQDN must not be empty', response.text)

    def test_update_labcontroller_with_invalid_fqdn(self):
        s = requests.Session()
        web_login(s)
        response = patch_json(
            get_server_base() + 'labcontrollers/' + self.lc.fqdn,
            session=s,
            data={'fqdn': u'invalid_lc_fqdn'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('Invalid FQDN for lab controller', response.text)

    # backwards compatibility
    # remove me once https://bugzilla.redhat.com/show_bug.cgi?id=1211119 is fixed
    def test_save_creates_labcontroller(self):
        s = requests.Session()
        web_login(s)
        fqdn = data_setup.unique_name('lc%s.com')
        data = {'fqdn': fqdn,
                'lusername': 'host/dev-kvm',
                'lpassword': 'testing',
                'email': 'root@dev-kvm.org'}
        response = s.post(
            get_server_base() + '/labcontrollers/save', data=data)

        self.assertEqual(response.status_code, 201)
        with session.begin():
            lc = LabController.query.filter_by(fqdn=data['fqdn']).one()
            self.assertEqual(lc.user.user_name, data['lusername'])
            self.assertEqual(lc.user.email_address, data['email'])
