#!/usr/bin/python
import unittest
import datetime
import sys
from tempfile import TemporaryFile
from turbogears.database import session
from bkr.server.model import SystemActivity
from bkr.server.test import data_setup
from bkr.server.test import mail_capture
from bkr.server.tools.nag_email import identify_nags

class TestNagMail(unittest.TestCase):

    @classmethod
    def setupClass(cls):
        cls.two_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
        cls.three_days_ago = datetime.datetime.now() - datetime.timedelta(days=3)

        cls.just_now = datetime.datetime.now()

        cls.user_1 = data_setup.create_user()
        cls.user_2 = data_setup.create_user()
        cls.system_1 = data_setup.create_system(owner=cls.user_1, shared=True)
        cls.system_2 = data_setup.create_system(owner=cls.user_1, shared=True)
        cls.system_3 = data_setup.create_system(owner=cls.user_2, shared=True)

        cls.subject_header = '[Beaker Reminder]: System'

        #Shouldn't send
        #This tests that mail is not sent if user == owner
        cls.system_1.user = cls.user_1
        cls.system_1.activity.append(SystemActivity(user=cls.user_1,
            service=u'WEBUI', action=u'Reserved', field_name=u'User', old_value=None,
            new_value=cls.user_1))
        cls.system_1.activity[-1].created = cls.two_days_ago

        #Shouldn't send
        #This tests that threshold value is honoured
        cls.system_2.user = cls.user_2
        cls.system_2.activity.append(SystemActivity(user=cls.user_2,
            service=u'WEBUI', action=u'Reserved', field_name=u'User',
            old_value=None, new_value=cls.user_2))
        cls.system_2.activity[-1].created = cls.just_now

        #Should send
        #This tests that with owner != user and taken > threshold, should send nag
        cls.system_3.user = cls.user_1
        cls.system_3.activity.append(SystemActivity(user=cls.user_1,
            service=u'WEBUI', action=u'Reserved', field_name=u'User',
            old_value=None, new_value=cls.user_1))
        cls.system_3.activity[-1].created = cls.three_days_ago
        session.flush()

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def test_nag_email_dry_run(self):
        days_had_system_for = 1
        testing = True
        service = u'WEBUI'
        f =  TemporaryFile()
        orig_out = sys.stdout
        sys.stdout = f
        identify_nags(days_had_system_for, service, testing)
        f.seek(0)
        nag_output = f.read()
        f.close()
        sys.stdout = orig_out #reset stdout back to original pointer
        self.assertEqual(len(self.mail_capture.captured_mails), 0)
        self.assert_('%s %s' % (self.subject_header, self.system_1.fqdn) not in nag_output)
        self.assert_('%s %s' % (self.subject_header, self.system_2.fqdn) not in nag_output)
        self.assert_('%s %s' % (self.subject_header, self.system_3.fqdn) in nag_output)

    def test_email_send(self):
        days_had_system_for = 1
        testing = False
        service = u'WEBUI'
        identify_nags(days_had_system_for, service, testing)
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        self.assert_('%s %s' % (self.subject_header, self.system_3.fqdn) in
            self.mail_capture.captured_mails[0][2])

    def tearDown(self):
        self.mail_capture.stop()

