
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import email
import re
import unittest2 as unittest
from turbogears.database import session
from bkr.server.model import Arch, TaskResult
from bkr.server.util import absolute_url
from bkr.inttest import data_setup, mail_capture, get_server_base
import bkr.server.mail

class BrokenSystemNotificationTest(unittest.TestCase):

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def test_broken_system_notification(self):
        with session.begin():
            owner = data_setup.create_user(email_address=u'ackbar@calamari.gov')
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(fqdn=u'home-one', owner=owner,
                    lender=u"Uncle Bob's Dodgy Shop", location=u'shed out the back',
                    lab_controller=lc, vendor=u'Acorn', arch=u'i386')
            system.arch.append(Arch.by_name(u'x86_64'))
            data_setup.configure_system_power(system, power_type=u'drac',
                    address=u'pdu2.home-one', power_id=u'42')

        with session.begin():
            bkr.server.mail.broken_system_notify(system, reason="It's a tarp!")
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        self.assertEqual(rcpts, ['ackbar@calamari.gov'])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], 'ackbar@calamari.gov')
        self.assertEqual(msg['Subject'],
                'System home-one automatically marked broken')
        self.assertEqual(msg['X-Beaker-Notification'], 'system-broken')
        self.assertEqual(msg['X-Beaker-System'], 'home-one')
        self.assertEqual(msg['X-Lender'], "Uncle Bob's Dodgy Shop")
        self.assertEqual(msg['X-Location'], 'shed out the back')
        self.assertEqual(msg['X-Lab-Controller'], lc.fqdn)
        self.assertEqual(msg['X-Vendor'], 'Acorn')
        self.assertEqual(msg['X-Type'], 'Machine')
        self.assertEqual(msg.get_all('X-Arch'), ['i386', 'x86_64'])
        self.assertEqual(msg.get_payload(decode=True),
                'Beaker has automatically marked system \n'
                'home-one <%sview/home-one> \n'
                'as broken, due to:\n\n'
                'It\'s a tarp!\n\n'
                'Please investigate this error and take appropriate action.\n\n'
                'Power type: drac\n'
                'Power address: pdu2.home-one\n'
                'Power id: 42'
                % get_server_base())

class SystemReservationNotificationTest(unittest.TestCase):

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def test_system_reserved_notification(self):
        with session.begin():
            owner = data_setup.create_user()
            job = data_setup.create_running_job(owner=owner)

        system = job.recipesets[0].recipes[0].resource.fqdn
        with session.begin():
            bkr.server.mail.reservesys_notify(job.recipesets[0].recipes[0], system)
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        self.assertEqual(rcpts, [owner.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], owner.email_address)
        self.assertEqual(msg['Subject'],
                '[Beaker System Reservation] System: %s' % system)
        self.assertEqual(msg['X-Beaker-Notification'], 'system-reservation')

        recipe = job.recipesets[0].recipes[0]
        system = recipe.resource.fqdn
        owner = job.owner.email_address
        expected_mail_body = u"""
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
                 This System is reserved by %s.

 To return this system early, you can click on 'Release System' against this recipe
 from the Web UI. Ensure you have your logs off the system before returning to 
 Beaker.

 For ssh, kvm, serial and power control operations please look here:
  %s

 For the default root password, see:
 %s

      Beaker Test information:
                         HOSTNAME=%s
                            JOBID=%s
                         RECIPEID=%s
                           DISTRO=%s
                     ARCHITECTURE=%s

      Job Whiteboard: %s

      Recipe Whiteboard: %s
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **""" \
        % (owner,
           absolute_url('/view/%s' % system),
           absolute_url('/prefs'),
           system, job.id,
           recipe.id, recipe.distro_tree,
           recipe.distro_tree.arch,
           job.whiteboard,
           recipe.whiteboard)
        actual_mail_body = msg.get_payload(decode=True)
        self.assertEqual(actual_mail_body, expected_mail_body)

class JobCompletionNotificationTest(unittest.TestCase):

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def test_subject_format(self):
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner)
            session.flush()
            data_setup.mark_job_complete(job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assert_('[Beaker Job Completion] [Completed/Pass]' in msg['Subject'])

    def test_job_owner_is_notified(self):
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner)
            session.flush()
            data_setup.mark_job_complete(job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([job_owner.email_address], rcpts)
        self.assertEqual(job_owner.email_address, msg['To'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

    def test_job_cc_list_is_notified(self):
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner,
                    cc=[u'dan@example.com', u'ray@example.com'])
            session.flush()
            data_setup.mark_job_complete(job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([job_owner.email_address, 'dan@example.com',
                'ray@example.com'], rcpts)
        self.assertEqual(job_owner.email_address, msg['To'])
        self.assertEqual('dan@example.com, ray@example.com', msg['Cc'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

    def test_contains_job_hyperlink(self):
        with session.begin():
            job = data_setup.create_job()
            session.flush()
            data_setup.mark_job_complete(job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        job_link = u'<%sjobs/%d>' % (get_server_base(), job.id)
        first_line = msg.get_payload(decode=True).splitlines()[0]
        self.assert_(job_link in first_line,
                'Job link %r should appear in first line %r'
                    % (job_link, first_line))

    # https://bugzilla.redhat.com/show_bug.cgi?id=720041
    def test_subject_contains_whiteboard(self):
        with session.begin():
            whiteboard = u'final space shuttle launch'
            job = data_setup.create_job(whiteboard=whiteboard)
            session.flush()
            data_setup.mark_job_complete(job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        # Subject header might be split across multiple lines
        subject = re.sub(r'\s+', ' ', msg['Subject'])
        self.assert_(whiteboard in subject, subject)

    def test_distro_name(self):
        with session.begin():
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertNotIn('Distro(', msg.get_payload(decode=True))

class GroupMembershipNotificationTest(unittest.TestCase):

    def setUp(self):
        self.mail_capture = mail_capture.MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def test_actions(self):

        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user()
            group = data_setup.create_group(owner=owner)
            member.groups.append(group)

        bkr.server.mail.group_membership_notify(member, group, owner, 'Added')
        self.assertEqual(len(self.mail_capture.captured_mails), 1)

        self.mail_capture.captured_mails[:] = []
        with session.begin():
            group.users.remove(member)

        bkr.server.mail.group_membership_notify(member, group, owner, 'Removed')
        self.assertEqual(len(self.mail_capture.captured_mails), 1)

        # invalid action
        try:
            bkr.server.mail.group_membership_notify(member, group, owner, 'Unchanged')
            self.fail('Must fail or die')
        except ValueError, e:
            self.assert_('Unknown action' in str(e))
