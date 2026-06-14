
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json
from bkr.inttest.assertions import assert_datetime_within
from bkr.inttest import data_setup, get_server_base, DatabaseTestCase
from bkr.server.model import SystemPermission, Note
from bkr.server.database import session

class SystemNoteHTTPTest(DatabaseTestCase):
    """
    Directly tests the HTTP interface for system notes.
    """

    def setUp(self):
        with session.begin():
            self.owner = data_setup.create_user(password=u'owner')
            self.system = data_setup.create_system(owner=self.owner)

    def test_add_note(self):
        note_text = 'sometimes it breaks'
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'owner')
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                session=s, data={'text': note_text})
        response.raise_for_status()
        with session.begin():
            session.expire_all()
            self.assertEqual(self.system.notes[0].user, self.owner)
            self.assertEqual(self.system.notes[0].text, note_text)
            assert_datetime_within(self.system.notes[0].created,
                    reference=datetime.datetime.utcnow(),
                    tolerance=datetime.timedelta(seconds=10))

    def test_empty_notes_are_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'owner')
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                session=s, data={'text': ''})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.text, 'Note text cannot be empty')

    def test_get_note(self):
        with session.begin():
            note_text = u'sometimes it works'
            self.system.notes.append(Note(text=note_text, user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
        response = requests.get(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id))
        response.raise_for_status()
        self.assertEqual(response.json()['id'], note_id)
        self.assertEqual(response.json()['text'], note_text)
        self.assertEqual(response.json()['user']['user_name'], self.owner.user_name)

    def test_mark_note_as_deleted(self):
        # Notes never get actually deleted, they just get marked as "deleted"
        # which hides them by default in the UI. "Obsoleted" would be a better
        # word but "deleted" is what we have.
        with session.begin():
            note_text = u'some obsolete info'
            self.system.notes.append(Note(text=note_text, user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'owner')
        response = patch_json(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id), session=s, data={'deleted': 'now'})
        response.raise_for_status()
        self.assertEqual(response.json()['id'], note_id)
        assert_datetime_within(
                datetime.datetime.strptime(response.json()['deleted'], '%Y-%m-%d %H:%M:%S'),
                reference=datetime.datetime.utcnow(),
                tolerance=datetime.timedelta(seconds=10))
        with session.begin():
            session.refresh(self.system.notes[0])
            assert_datetime_within(self.system.notes[0].deleted,
                    reference=datetime.datetime.utcnow(),
                    tolerance=datetime.timedelta(seconds=10))

    def test_user_with_edit_permission_can_add_note(self):
        with session.begin():
            user = data_setup.create_user(password='password')
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, user=user)
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                session=s, data={'text': 'asdf'})
        response.raise_for_status()

    def test_user_with_edit_permission_can_delete_note(self):
        with session.begin():
            self.system.notes.append(Note(text=u'asdf', user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
            user = data_setup.create_user(password='password')
            self.system.custom_access_policy.add_rule(
                    permission=SystemPermission.edit_system, user=user)
        s = requests.Session()
        requests_login(s, user=user.user_name, password=u'password')
        response = patch_json(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id), session=s, data={'deleted': 'now'})
        response.raise_for_status()

    def test_unprivileged_user_cannot_add_note(self):
        with session.begin():
            unprivileged = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=unprivileged.user_name, password=u'password')
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                session=s, data={'text': 'asdf'})
        self.assertEqual(response.status_code, 403)

    def test_unprivileged_user_cannot_delete_note(self):
        with session.begin():
            self.system.notes.append(Note(text=u'asdf', user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
            unprivileged = data_setup.create_user(password=u'password')
        s = requests.Session()
        requests_login(s, user=unprivileged.user_name, password=u'password')
        response = patch_json(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id), session=s, data={'deleted': 'now'})
        self.assertEqual(response.status_code, 403)

    def test_anonymous_cannot_add_note(self):
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                data={'text': 'asdf'})
        self.assertEqual(response.status_code, 401)

    def test_anonymous_cannot_delete_note(self):
        with session.begin():
            self.system.notes.append(Note(text=u'asdf', user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
        response = patch_json(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id), data={'deleted': 'now'})
        self.assertEqual(response.status_code, 401)
