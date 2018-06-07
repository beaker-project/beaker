
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import email
import re
import uuid
from turbogears.database import session
from bkr.server.model import Arch, TaskResult
from bkr.server.util import absolute_url
from bkr.inttest import data_setup, mail_capture_thread, get_server_base, \
        DatabaseTestCase
import bkr.server.mail
from bkr.server.mail import failed_recipes
from datetime import datetime, timedelta
from bkr.server.tools.usage_reminder import BeakerUsage


class BrokenSystemNotificationTest(DatabaseTestCase):

    def test_broken_system_notification_on(self):
        with session.begin():
            owner = data_setup.create_user(email_address=u'ackbar@calamari.gov')
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(fqdn=u'home-one', owner=owner,
                    lender=u"Uncle Bob's Dodgy Shop", location=u'shed out the back',
                    lab_controller=lc, vendor=u'Acorn', arch=u'i386')
            system.arch.append(Arch.by_name(u'x86_64'))
            data_setup.configure_system_power(system, power_type=u'drac',
                    address=u'pdu2.home-one', power_id=u'42')

        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.broken_system_notify(system, reason="It's a tarp!")
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
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

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_broken_system_notification_off(self):
        with session.begin():
            owner = data_setup.create_user(email_address=u'derp@derpmail.com',
                                           notify_broken_system=False)
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(fqdn=u'home-two', owner=owner,
                                              lender=u"Aunty Jane's Dodgy Shop",
                                              location=u'shed out the front',
                                              lab_controller=lc,
                                              vendor=u'Acorn', arch=u'i386')
            system.arch.append(Arch.by_name(u'x86_64'))
            data_setup.configure_system_power(system, power_type=u'drac',
                                              address=u'pdu3.home-one',
                                              power_id=u'42')
        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.broken_system_notify(system, reason="It's not a tarp!")
        captured_mails = mail_capture_thread.stop_capturing(wait=False)
        self.assertEqual(len(captured_mails), 0)


class SystemReservationNotificationTest(DatabaseTestCase):

    maxDiff = None

    def test_system_reserved_notification_on(self):
        with session.begin():
            owner = data_setup.create_user(
                    email_address=u'lizlemon@kabletown.com')
            system = data_setup.create_system(fqdn=u'funcooker.ge.invalid',
                    lab_controller=data_setup.create_labcontroller())
            distro_tree = data_setup.create_distro_tree(distro_name=u'MicrowaveOS-20141016.0',
                    variant=u'ThreeHeats', arch=u'x86_64')
            job = data_setup.create_running_job(owner=owner, system=system,
                    distro_tree=distro_tree,
                    whiteboard=u'Chain Reaction of Mental Anguish',
                    recipe_whiteboard=u'Christmas Attack Zone')
            recipe = job.recipesets[0].recipes[0]

        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.reservesys_notify(job.recipesets[0].recipes[0])
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        self.assertEqual(rcpts, [owner.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], owner.email_address)
        self.assertEqual(msg['Subject'],
                '[Beaker System Reserved] funcooker.ge.invalid')
        self.assertEqual(msg['X-Beaker-Notification'], 'system-reservation')

        expected_mail_body = u"""\
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
                 This System is reserved by lizlemon@kabletown.com

 To return this system early, you can click on 'Release System' against this recipe
 from the Web UI. Ensure you have your logs off the system before returning to
 Beaker.
  %(base)srecipes/%(recipeid)s

 For ssh, kvm, serial and power control operations please look here:
  %(base)sview/funcooker.ge.invalid

 For the default root password, see:
  %(base)sprefs

      Beaker Test information:
                         HOSTNAME=funcooker.ge.invalid
                            JOBID=%(jobid)s
                         RECIPEID=%(recipeid)s
                           DISTRO=MicrowaveOS-20141016.0 ThreeHeats x86_64
                     ARCHITECTURE=x86_64

      Job Whiteboard: Chain Reaction of Mental Anguish

      Recipe Whiteboard: Christmas Attack Zone
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **""" \
            % dict(base=get_server_base(), recipeid=recipe.id, jobid=job.id)
        actual_mail_body = msg.get_payload(decode=True)
        self.assertEqual(actual_mail_body, expected_mail_body)

    def test_reserved_openstack_instance(self):
        with session.begin():
            owner = data_setup.create_user(
                    email_address=u'jackdonaghy@kabletown.com')
            distro_tree = data_setup.create_distro_tree(distro_name=u'MicrowaveOS-20141016.1',
                    variant=u'ThreeHeats', arch=u'x86_64')
            job = data_setup.create_job(owner=owner,
                    distro_tree=distro_tree,
                    whiteboard=u'Operation Righteous Cowboy Lightning',
                    recipe_whiteboard=u'Everything Sunny All the Time Always')
            recipe = job.recipesets[0].recipes[0]
            data_setup.mark_recipe_running(recipe,
                    virt=True, instance_id=uuid.UUID('00000000-1111-2222-3333-444444444444'),
                    fqdn=u'bitenuker.ge.invalid')

        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.reservesys_notify(recipe)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        self.assertEqual(rcpts, [owner.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], owner.email_address)
        self.assertEqual(msg['Subject'],
                '[Beaker System Reserved] bitenuker.ge.invalid')
        self.assertEqual(msg['X-Beaker-Notification'], 'system-reservation')

        expected_mail_body = u"""\
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **
                 This System is reserved by jackdonaghy@kabletown.com

 To return this system early, you can click on 'Release System' against this recipe
 from the Web UI. Ensure you have your logs off the system before returning to
 Beaker.
  %(base)srecipes/%(recipeid)s

 For system details, see:
  http://openstack.example.invalid/dashboard/project/instances/00000000-1111-2222-3333-444444444444/

 For the default root password, see:
  %(base)sprefs

      Beaker Test information:
                         HOSTNAME=bitenuker.ge.invalid
                            JOBID=%(jobid)s
                         RECIPEID=%(recipeid)s
                           DISTRO=MicrowaveOS-20141016.1 ThreeHeats x86_64
                     ARCHITECTURE=x86_64

      Job Whiteboard: Operation Righteous Cowboy Lightning

      Recipe Whiteboard: Everything Sunny All the Time Always
**  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **  **""" \
            % dict(base=get_server_base(), recipeid=recipe.id, jobid=job.id)
        actual_mail_body = msg.get_payload(decode=True)
        self.assertMultiLineEqual(actual_mail_body, expected_mail_body)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_system_reserved_notification_off(self):
        with session.begin():
            owner = data_setup.create_user(email_address=u'derp@derptown.com',
                                           notify_reservesys=False)
            system = data_setup.create_system(fqdn=u'funcooker.ge.valid',
                    lab_controller=data_setup.create_labcontroller())
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64')
            job = data_setup.create_running_job(owner=owner, system=system,
                    distro_tree=distro_tree,
                    whiteboard=u'This is a whiteboard',
                    recipe_whiteboard=u'This is another whiteboard')

        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.reservesys_notify(job.recipesets[0].recipes[0])
        captured_mails = mail_capture_thread.stop_capturing(wait=False)
        self.assertEqual(len(captured_mails), 0)


class JobCompletionNotificationTest(DatabaseTestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=911515
    def test_failed_recipe_mail_started_before_upgrade_does_not_crash(self):
        with session.begin():
            job = data_setup.create_completed_job(result=TaskResult.fail)
            # recipes that started before the upgrade wont have these parameters...
            job.recipesets[0].recipes[0].installation.arch = None
            job.recipesets[0].recipes[0].installation.distro_name = None
            job.recipesets[0].recipes[0].installation.variant = None
            job.recipesets[0].recipes[0].installation.osmajor = None
            job.recipesets[0].recipes[0].installation.osminor = None
        msg = failed_recipes(job)
        self.assertIn('Completed Result: Fail', msg)

    def test_subject_format(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner)
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assert_('[Beaker Job Completion] [Completed/Pass]' in msg['Subject'])

    def test_job_owner_is_notified(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner)
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([job_owner.email_address], rcpts)
        self.assertEqual(job_owner.email_address, msg['To'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

    def test_job_cc_list_is_notified(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job_owner = data_setup.create_user()
            job = data_setup.create_job(owner=job_owner,
                    cc=[u'dan@example.com', u'ray@example.com'])
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([job_owner.email_address, 'dan@example.com',
                'ray@example.com'], rcpts)
        self.assertEqual(job_owner.email_address, msg['To'])
        self.assertEqual('dan@example.com, ray@example.com', msg['Cc'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

    def test_contains_job_hyperlink(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job = data_setup.create_job()
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        job_link = u'<%sjobs/%d>' % (get_server_base(), job.id)
        first_line = msg.get_payload(decode=True).splitlines()[0]
        self.assert_(job_link in first_line,
                'Job link %r should appear in first line %r'
                    % (job_link, first_line))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1326968
    def test_contains_recipe_hyperlink(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_job_complete(job, result=TaskResult.fail)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        recipe_link = u'<%srecipes/%d' % (get_server_base(), recipe.id)
        recipe_line = msg.get_payload(decode=True).splitlines()[2]
        self.assertIn(recipe_link, recipe_line)

    # https://bugzilla.redhat.com/show_bug.cgi?id=720041
    def test_subject_contains_whiteboard(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            whiteboard = u'final space shuttle launch'
            job = data_setup.create_job(whiteboard=whiteboard)
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        # Subject header might be split across multiple lines
        subject = re.sub(r'\s+', ' ', msg['Subject'])
        self.assert_(whiteboard in subject, subject)

    def test_distro_name(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, result=TaskResult.fail)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertNotIn('Distro(', msg.get_payload(decode=True))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_job_completion_notification_off(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job_owner = data_setup.create_user(notify_job_completion=False)
            job = data_setup.create_job(owner=job_owner)
            session.flush()
            data_setup.mark_job_complete(job)

        captured_mails = mail_capture_thread.stop_capturing(wait=False)
        self.assertEqual(len(captured_mails), 0)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1588263
    def test_headers_for_avoiding_autoreplies(self):
        mail_capture_thread.start_capturing()
        with session.begin():
            job = data_setup.create_job()
            data_setup.mark_job_complete(job)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)
        sender, rcpts, raw_msg = captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEquals(msg['Auto-Submitted'], 'auto-generated')
        self.assertEquals(msg['Precedence'], 'bulk')


class GroupMembershipNotificationTest(DatabaseTestCase):

    def test_actions(self):

        with session.begin():
            owner = data_setup.create_user()
            member = data_setup.create_user()
            group = data_setup.create_group(owner=owner)
            group.add_member(member)

        mail_capture_thread.start_capturing()
        bkr.server.mail.group_membership_notify(member, group, owner, 'Added')
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)

        with session.begin():
            group.remove_member(member)

        mail_capture_thread.start_capturing()
        bkr.server.mail.group_membership_notify(member, group, owner, 'Removed')
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails), 1)

        # invalid action
        try:
            bkr.server.mail.group_membership_notify(member, group, owner, 'Unchanged')
            self.fail('Must fail or die')
        except ValueError, e:
            self.assert_('Unknown action' in str(e))

    # https://bugzilla.redhat.com/show_bug.cgi?id=1136748
    def test_group_membership_notification_off(self):
        with session.begin():
            owner = data_setup.create_user(notify_group_membership=False)
            member = data_setup.create_user(notify_group_membership=False)

            # group data_setup has not been changed, mail may sneak thru
            group = data_setup.create_group(owner=owner)
            group.add_member(member)

        mail_capture_thread.start_capturing()
        bkr.server.mail.group_membership_notify(member, group, owner, 'Added')
        captured_mails = mail_capture_thread.stop_capturing(wait=False)
        self.assertEqual(len(captured_mails), 0)


class UsageReminderTest(DatabaseTestCase):

    def setUp(self):
        self.user = data_setup.create_user()
        self.reservation_expiry = 24
        self.reservation_length = 3
        self.waiting_recipe_age = 1
        self.delayed_job_age = 14

    def _create_expiring_reservation(self):
        recipe = data_setup.create_recipe_reservation(self.user, u'/distribution/reservesys',
                                                      (self.reservation_expiry - 1) * 3600)
        email_content = u"""
Your reservations of the following systems in %s are going to expire within %s hours.
If you wish to ensure you retain the contents of these systems, please extend your reservation.

Expiry Date              FQDN
%s      %s
"""     % (absolute_url('/'),
           self.reservation_expiry,
           recipe.watchdog.kill_time.strftime('%Y-%m-%d %H:%M:%S'),
           recipe.resource.fqdn)
        return email_content

    def _create_open_reservation(self):
        system = data_setup.create_system()
        data_setup.create_manual_reservation(system,
                                             start=datetime.utcnow() - timedelta(days=self.reservation_length),
                                             user=self.user)
        recipe = data_setup.create_recipe()
        recipe.systems[:] = [system]
        job = data_setup.create_job_for_recipes([recipe])
        data_setup.mark_job_queued(job)
        job.recipesets[0].queue_time = datetime.utcnow() - timedelta(hours=self.waiting_recipe_age)
        email_content = u"""
The following systems have been allocated to you in %s for more than %s days and have other
recipes queued for longer than %s hours. Please return them if you are no longer using them.

Duration                 Waiting                  FQDN
%s                   %s                 %s
"""    % (absolute_url('/'),
          self.reservation_length,
          self.waiting_recipe_age,
          "%s days" % (datetime.utcnow() - system.reservations[0].start_time).days,
          "1 recipe",
          system.fqdn)
        return email_content

    def _create_delayed_job(self):
        recipe = data_setup.create_recipe()
        job = data_setup.create_job_for_recipes([recipe])
        job.owner = self.user
        data_setup.mark_job_queued(job)
        job.recipesets[0].queue_time = datetime.utcnow() - timedelta(days=self.delayed_job_age)
        email_content = u"""
The following jobs you submitted to %s have been queued for more than %s days. Please cancel
them if they are no longer relevant, or perhaps arrange a loan of an appropriate system or systems

Start time               Delayed Job
%s      %s
"""     % (absolute_url('/'),
           self.delayed_job_age,
           job.recipesets[0].queue_time.strftime('%Y-%m-%d %H:%M:%S'),
           absolute_url('/jobs/%s') % job.id)
        return email_content

    def test_send_usage_reminder(self):
        with session.begin():
            email_content = self._create_expiring_reservation()
            email_content += self._create_open_reservation()
            email_content += self._create_delayed_job()

        beaker_usage = BeakerUsage(self.user, self.reservation_expiry, self.reservation_length,
                                   self.waiting_recipe_age, self.delayed_job_age)
        current_date = datetime.utcnow().strftime("%Y-%m-%d")
        data = {
            'user_name': self.user.user_name,
            'current_date': current_date,
            'beaker_fqdn': absolute_url('/'),
            'reservation_expiry': self.reservation_expiry,
            'reservation_length': self.reservation_length,
            'waiting_recipe_age': self.waiting_recipe_age,
            'delayed_job_age': self.delayed_job_age,
            'expiring_reservations': beaker_usage.expiring_reservations(),
            'open_reservations': beaker_usage.open_in_demand_systems(),
            'delayed_jobs': beaker_usage.delayed_jobs()
        }

        mail_capture_thread.start_capturing()
        with session.begin():
            bkr.server.mail.send_usage_reminder(self.user, data)
        captured_mails = mail_capture_thread.stop_capturing()
        self.assertEqual(len(captured_mails),1)
        sender, rcpts, raw_msg = captured_mails[0]
        self.assertEqual(rcpts, [self.user.email_address])
        msg = email.message_from_string(raw_msg)
        self.assertEqual(msg['To'], self.user.email_address)
        self.assertTrue(msg['Subject'], '[Beaker] Usage report for %s (%s)' % (self.user.user_name, current_date))
        expected_mail_body = u"""=========
[Beaker] Usage report for %s (%s)
=========

Hi %s,
%s
=========""" % (self.user.user_name,
                current_date,
                self.user.user_name,
                email_content)
        actual_mail_body = msg.get_payload(decode=True)
        self.assertEqual(actual_mail_body, expected_mail_body)
        self.assertEqual(msg['X-Beaker-Notification'], 'usage-report')
