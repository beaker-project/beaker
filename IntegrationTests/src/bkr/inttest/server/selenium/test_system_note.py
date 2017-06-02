
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import requests
from bkr.inttest.server.requests_utils import login as requests_login, \
        patch_json, post_json
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest.assertions import wait_for_condition, assert_datetime_within
from bkr.inttest import data_setup, with_transaction, get_server_base, \
        DatabaseTestCase
from bkr.server.model import SystemPermission, Note
from turbogears.database import session

class SystemNoteTests(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.owner = data_setup.create_user(password='password')
        self.system.owner = self.owner
        self.nobody = data_setup.create_user(password='password')
        self.browser = self.get_browser()

    def go_to_notes_tab(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_xpath('//title[normalize-space(text())="%s"]'
                % self.system.fqdn)
        b.find_element_by_xpath('//ul[contains(@class, "system-nav")]'
                '//a[text()="Notes"]').click()
        return b.find_element_by_id('notes')

    def test_no_notes(self):
        pane = self.go_to_notes_tab()
        self.assertEquals(pane.find_element_by_xpath('p[1]').text,
                'No notes have been recorded for this system.')

    def add_note(self):
        pane = self.go_to_notes_tab()
        note = data_setup.unique_name('note%s')
        pane.find_element_by_name('text').send_keys(note)
        pane.find_element_by_tag_name('form').submit()
        # Wait for it to appear
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % note)
        return note

    def delete_note(self, note):
        b = self.browser
        pane = b.find_element_by_id('notes')
        note_div = pane.find_element_by_xpath('div[@class="system-note" '
                'and div[@class="system-note-text"]/p[text()="%s"]]' % note)
        note_div.find_element_by_xpath('.//button[normalize-space(string(.))="Delete"]').click()
        modal = b.find_element_by_class_name('modal')
        modal.find_element_by_xpath('.//p[text()="Are you sure you want to delete this note?"]')
        modal.find_element_by_xpath('.//button[text()="OK"]').click()
        # Test that it is hidden
        b.find_element_by_xpath('//div[@id="notes" and '
                'not(.//div[@class="system-note-text"]/p[text()="%s"])]' % note)

    def test_can_show_deleted_notes(self):
        note_text = u'deleteme'
        with session.begin():
            self.system.notes.append(Note(text=note_text, user=self.owner))
        b = self.browser
        login(b)
        pane = self.go_to_notes_tab()
        self.delete_note(note_text)
        # Test that we have acreated a new element to toggle the notes
        deleted_div = pane.find_element_by_xpath('div[@class="deleted-system-notes"]')
        self.assertEquals(deleted_div.text, '1 deleted note is not shown Show')
        deleted_div.find_element_by_xpath('button[text()="Show"]').click()
        # Test that it reappears when toggled
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % note_text)

    def test_notes_are_hidden_by_default(self):
        note_text = u'something-deleted'
        with session.begin():
            self.system.notes.append(Note(text=note_text, user=self.owner))
            self.system.notes[0].deleted = datetime.datetime.utcnow()
        pane = self.go_to_notes_tab()
        # Test existing deleted notes are hidden
        deleted_div = pane.find_element_by_xpath('div[@class="deleted-system-notes"]')
        self.assertEquals(deleted_div.text, '1 deleted note is not shown Show')
        deleted_div.find_element_by_xpath('button[text()="Show"]').click()
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % note_text)

    def test_multiple_hidden_notes(self):
        b = self.browser
        login(b)
        note = self.add_note()
        self.delete_note(note)
        # Add another note, delete it, and then toggle to make sure
        # both of the deleted notes display together, and are hidden together
        note_2 = self.add_note()
        self.delete_note(note_2)
        pane = b.find_element_by_id('notes')
        pane.find_element_by_xpath('.//button[text()="Show"]').click()
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % note)
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % note_2)

    def test_notes_as_owner(self):
        login(self.browser, user=self.owner.user_name, password='password')
        note = self.add_note()
        self.delete_note(note)

    def test_notes_as_nobody(self):
        with session.begin():
            self.system.notes.append(Note(text=u'something', user=self.owner))
        login(self.browser, user=self.nobody.user_name, password=u'password')
        self.go_to_notes_tab()
        b = self.browser
        # Test that we cannot add another as unprivileged user
        b.find_element_by_xpath('//div[@id="notes" and '
                'not(.//button[normalize-space(string(.))="Add"])]')
        # Delete button should also not be present
        b.find_element_by_xpath('//div[@id="notes" and '
                'not(.//button[normalize-space(string(.))="Delete"])]')

    def test_notes_logged_out(self):
        with session.begin():
            self.system.notes.append(Note(text=u'something', user=self.owner))
        b = self.browser
        self.go_to_notes_tab()
        # Test that we cannot add another note without logging in
        b.find_element_by_xpath('//div[@id="notes" and '
                'not(.//button[normalize-space(string(.))="Add"])]')
        # Delete button should also not be present
        b.find_element_by_xpath('//div[@id="notes" and '
                'not(.//button[normalize-space(string(.))="Delete"])]')

    def test_markdown_formatting(self):
        note_text = '''Here is my note.

It has multiple paragraphs, *and emphasis*.
Also a URL <http://example.com/>.'''
        with session.begin():
            self.system.notes.append(Note(text=note_text, user=self.owner))
        pane = self.go_to_notes_tab()
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[1][text()="Here is my note."]')
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[2][em/text()="and emphasis"]')
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[2][a/@href="http://example.com/"]')

    # https://bugzilla.redhat.com/show_bug.cgi?id=1014870
    def test_html_is_escaped(self):
        bad_note = 'Console is available via: console -l <user> <system_fqdn>'
        with session.begin():
            self.system.notes.append(Note(text=bad_note, user=self.owner))
        pane = self.go_to_notes_tab()
        pane.find_element_by_xpath('div[@class="system-note"]'
                '/div[@class="system-note-text"]/p[text()="%s"]' % bad_note)

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
            self.assertEquals(self.system.notes[0].user, self.owner)
            self.assertEquals(self.system.notes[0].text, note_text)
            assert_datetime_within(self.system.notes[0].created,
                    reference=datetime.datetime.utcnow(),
                    tolerance=datetime.timedelta(seconds=10))

    def test_empty_notes_are_rejected(self):
        s = requests.Session()
        requests_login(s, user=self.owner.user_name, password=u'owner')
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                session=s, data={'text': ''})
        self.assertEquals(response.status_code, 400)
        self.assertEquals(response.content, 'Note text cannot be empty')

    def test_get_note(self):
        with session.begin():
            note_text = u'sometimes it works'
            self.system.notes.append(Note(text=note_text, user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
        response = requests.get(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id))
        response.raise_for_status()
        self.assertEquals(response.json()['id'], note_id)
        self.assertEquals(response.json()['text'], note_text)
        self.assertEquals(response.json()['user']['user_name'], self.owner.user_name)

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
        self.assertEquals(response.json()['id'], note_id)
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
        self.assertEquals(response.status_code, 403)

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
        self.assertEquals(response.status_code, 403)

    def test_anonymous_cannot_add_note(self):
        response = post_json(get_server_base() + 'systems/%s/notes/' % self.system.fqdn,
                data={'text': 'asdf'})
        self.assertEquals(response.status_code, 401)

    def test_anonymous_cannot_delete_note(self):
        with session.begin():
            self.system.notes.append(Note(text=u'asdf', user=self.owner))
            session.flush()
            note_id = self.system.notes[0].id
        response = patch_json(get_server_base() + 'systems/%s/notes/%s'
                % (self.system.fqdn, note_id), data={'deleted': 'now'})
        self.assertEquals(response.status_code, 401)
