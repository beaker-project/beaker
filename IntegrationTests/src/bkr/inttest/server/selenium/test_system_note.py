from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, logout
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest import data_setup, with_transaction, get_server_base
from turbogears.database import session

class SystemNoteTests(WebDriverTestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.owner = data_setup.create_user(password='password')
        self.system.owner = self.owner
        self.admin_group = data_setup.create_group()
        self.user = data_setup.create_user(password='password')
        self.admin_group.users.append(self.user)
        data_setup.add_group_to_system(self.system, self.admin_group, admin=True)
        self.nobody = data_setup.create_user(password='password')
        self.browser = self.get_browser()

    def tearDown(self):
        self.browser.quit()

    def add_note(self):
        b = self.browser
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('Notes').click()
        note = data_setup.unique_name('note%s')
        b.find_element_by_id('notes_note').send_keys(note)
        b.find_element_by_xpath("//form[@name='notes']//a[normalize-space(text())='Add ( + )']").click()
        note_p = b.find_element_by_xpath('//td[preceding-sibling::th[text()="Note"]]/div/p')
        self.assertEquals(note_p.text, note)
        return note

    def delete_note(self, note):
        b = self.browser
        b.find_element_by_link_text('Notes').click()
        b.find_element_by_xpath('//a[text()="(Delete this note)" and '
            'preceding-sibling::div/p/text()="%s"]' % note).click()
        # Test confirmation dialogue
        b.find_element_by_xpath(
                '//div[.//p/text()="Are you sure you want to delete this?"]'
                '//button[text()="Yes"]').click()
        # Test that it is hidden
        wait_for_condition(lambda: not b.find_element_by_xpath(
                '//tr[th/text()="Note" and td/div/p/text()="%s"]' % note)
                .is_displayed())

    def test_can_show_deleted_notes(self):
        b = self.browser
        login(b)
        note = self.add_note()
        self.delete_note(note)
        # Test that we have acreated a new element to toggle the notes
        b.find_element_by_link_text('Toggle deleted notes').click()
        # Test that it reappears when toggled
        wait_for_condition(lambda: b.find_element_by_xpath(
                '//tr[th/text()="Note" and td/div/p/text()="%s"]' % note)
                .is_displayed())

    def test_notes_are_hidden_by_default(self):
        b = self.browser
        login(b)
        note = self.add_note()
        self.delete_note(note)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('Notes').click()
        # Test existing deleted notes are hidden
        self.assertFalse(b.find_element_by_xpath(
                '//tr[th/text()="Note" and td/div/p/text()="%s"]' % note)
                .is_displayed())
        # Test that it recognises deleted notes and gives us a toggle option
        b.find_element_by_link_text('Toggle deleted notes')

    def test_multiple_hidden_notes(self):
        b = self.browser
        login(b)
        note = self.add_note()
        self.delete_note(note)
        # Add another note, delete it, and then toggle to make sure
        # both of the deleted notes display together, and are hidden together
        note_2 = self.add_note()
        self.delete_note(note_2)
        b.find_element_by_link_text('Toggle deleted notes').click()
        wait_for_condition(lambda: b.find_element_by_xpath(
                '//tr[th/text()="Note" and td/div/p/text()="%s"]' % note)
                .is_displayed())
        wait_for_condition(lambda: b.find_element_by_xpath(
                '//tr[th/text()="Note" and td/div/p/text()="%s"]' % note_2)
                .is_displayed())

    def test_notes_as_admin(self):
        login(self.browser)
        note = self.add_note()
        self.delete_note(note)

    def test_notes_as_owner(self):
        login(self.browser, user=self.owner.user_name, password='password')
        note = self.add_note()
        self.delete_note(note)

    def test_notes_as_group_admin(self):
        login(self.browser, user=self.user.user_name, password='password')
        note = self.add_note()
        self.delete_note(note)

    def test_notes_as_nobody(self):
        # Add a note by authorised user
        login(self.browser)
        note = self.add_note()

        # Test that we cannot add another as unprivileged user
        logout(self.browser)
        login(self.browser, user=self.nobody.user_name, password='password')
        try:
            self.add_note()
        except Exception:
            pass
        else:
            raise AssertionError('Unprivileged user was able to add note')

        #Try to delete the first added note
        try:
            self.delete_note(note)
        except Exception:
            pass
        else:
            raise AssertionError('Unprivileged user was able to delete a note')

    def test_notes_logged_out(self):
        # Add a note by authorised user
        login(self.browser)
        note = self.add_note()

        # Test that we cannot add another note without logging in
        logout(self.browser)
        try:
            self.add_note()
        except Exception:
            pass
        else:
            raise AssertionError('User without credentials was able to add note')

        #Try to delete the first added note
        try:
            self.delete_note(note)
        except Exception:
            pass
        else:
            raise AssertionError('User without credentials was able to delete a note')

    def test_markdown_formatting(self):
        b = self.browser
        login(b)
        b.get(get_server_base() + 'view/%s' % self.system.fqdn)
        b.find_element_by_link_text('Notes').click()
        b.find_element_by_id('notes_note').send_keys('''Here is my note.

It has multiple paragraphs, *and emphasis*.
Also a URL <http://example.com/>.''')
        b.find_element_by_xpath("//form[@name='notes']//a[normalize-space(text())='Add ( + )']").click()
        b.find_element_by_xpath('//td[preceding-sibling::th[text()="Note"]]/div'
                '/p[1][text()="Here is my note."]')
        b.find_element_by_xpath('//td[preceding-sibling::th[text()="Note"]]/div'
                '/p[2][em/text()="and emphasis"]')
        b.find_element_by_xpath('//td[preceding-sibling::th[text()="Note"]]/div'
                '/p[2][a/@href="http://example.com/"]')
