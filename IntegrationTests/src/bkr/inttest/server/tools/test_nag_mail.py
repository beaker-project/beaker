#!/usr/bin/python
import unittest
import datetime
import sys
from tempfile import TemporaryFile
from turbogears.database import session
from bkr.server.model import SystemActivity, SystemStatus
from bkr.inttest import data_setup, mail_capture, with_transaction
from bkr.server.tools.nag_email import identify_nags

class TestNagMail(unittest.TestCase):

    @classmethod
    @with_transaction
    def setupClass(cls):
        cls.two_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        cls.three_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=3)

        cls.just_now = datetime.datetime.utcnow()

        cls.user_1 = data_setup.create_user()
        cls.user_2 = data_setup.create_user()
        def _create_system(user):
            return data_setup.create_system(owner=user, shared=True,
                                            status=SystemStatus.manual)
        cls.system_1 = _create_system(cls.user_1)
        cls.system_2 = _create_system(cls.user_1)
        cls.system_3 = _create_system(cls.user_2)

        cls.subject_header = '[Beaker Reminder]: System'

        #Shouldn't send
        #This tests that mail is not sent if user == owner
        cls.system_1.reserve_manually(service=u'testdata', user=cls.user_1)
        cls.system_1.reservations[-1].start_time = cls.two_days_ago

        #Shouldn't send
        #This tests that threshold value is honoured
        cls.system_2.reserve_manually(service=u'testdata', user=cls.user_2)
        cls.system_2.reservations[-1].start_time = cls.just_now

        #Should send
        #This tests that with owner != user and taken > threshold, should send nag
        cls.system_3.reserve_manually(service=u'testdata', user=cls.user_1)
        cls.system_3.reservations[-1].start_time = cls.three_days_ago

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def test_nag_email_dry_run(self):
        days_had_system_for = 1
        testing = True
        reservation_type = u'manual'
        f =  TemporaryFile()
        orig_out = sys.stdout
        sys.stdout = f
        identify_nags(days_had_system_for, reservation_type, testing)
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
        reservation_type = u'manual'
        identify_nags(days_had_system_for, reservation_type, testing)
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        self.assert_('%s %s' % (self.subject_header, self.system_3.fqdn) in
            self.mail_capture.captured_mails[0][2])

    def tearDown(self):
        self.mail_capture.stop()

