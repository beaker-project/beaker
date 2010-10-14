import sys
import time
import unittest
import email
from turbogears.database import session
from bkr.server.model import System, SystemStatus, SystemActivity, TaskStatus, \
        Job, JobCc, job_cc_table
from bkr.server.test import data_setup
from bkr.server.test.mail_capture import MailCaptureThread

# workaround for weird sqlalchemy-0.4 bug :-S
# http://markmail.org/message/rnnzdebfzrjt3kmi
from sqlalchemy.orm.dynamic import DynamicAttributeImpl
DynamicAttributeImpl.accepts_scalar_loader = False

class TestSystem(unittest.TestCase):

    def test_create_system_params(self):
        new_system = System(fqdn='test_fqdn', contact='test@email.com',
                            location='Brisbane', model='Proliant', serial='4534534',
                            vendor='Dell')
        self.assertEqual(new_system.fqdn, 'test_fqdn')
        self.assertEqual(new_system.contact, 'test@email.com')
        self.assertEqual(new_system.location, 'Brisbane')
        self.assertEqual(new_system.model, 'Proliant')
        self.assertEqual(new_system.serial, '4534534')
        self.assertEqual(new_system.vendor, 'Dell')
    
    def test_add_user_to_system(self): 
        user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = user
        self.assertEquals(system.user, user)

    def test_remove_user_from_system(self):
        user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = user
        system.user = None
        self.assert_(system.user is None)

class TestBrokenSystemDetection(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=637260
    # The 1-second sleeps here are so that the various timestamps
    # don't end up within the same second

    def setUp(self):
        self.system = data_setup.create_system()
        self.system.status = SystemStatus.by_name(u'Automated')
        self.system.activity.append(SystemActivity(service=u'Test data',
                action=u'Changed', field_name=u'Status',
                old_value=None, new_value=self.system.status))
        data_setup.create_completed_job(system=self.system)
        session.flush()
        time.sleep(1)

    def abort_recipe_with_stable_distro(self, distro=None):
        if distro is None:
            distro = data_setup.create_distro()
            distro.tags.append(u'STABLE')
        recipe = data_setup.create_recipe(distro=distro)
        data_setup.create_job_for_recipes([recipe])
        recipe.system = self.system
        recipe.tasks[0].status = TaskStatus.by_name(u'Running')
        recipe.update_status()
        session.flush()
        recipe.abort()

    def test_multiple_suspicious_aborts_triggers_broken_system(self):
        # first aborted recipe shouldn't trigger it
        self.abort_recipe_with_stable_distro()
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        # another recipe with a different stable distro *should* trigger it
        self.abort_recipe_with_stable_distro()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))

    def test_status_change_is_respected(self):
        # two aborted recipes should trigger it...
        self.abort_recipe_with_stable_distro()
        self.abort_recipe_with_stable_distro()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        # then the owner comes along and marks it as fixed...
        self.system.status = SystemStatus.by_name(u'Automated')
        self.system.activity.append(SystemActivity(service=u'WEBUI',
                action=u'Changed', field_name=u'Status',
                old_value=SystemStatus.by_name(u'Broken'),
                new_value=self.system.status))
        session.flush()
        time.sleep(1)
        # another recipe aborts...
        self.abort_recipe_with_stable_distro()
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken')) # not broken! yet
        self.abort_recipe_with_stable_distro()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken')) # now it is

    def test_counts_distinct_stable_distros(self):
        first_distro = data_setup.create_distro()
        first_distro.tags.append(u'STABLE')
        # two aborted recipes for the same distro shouldn't trigger it
        self.abort_recipe_with_stable_distro(distro=first_distro)
        self.abort_recipe_with_stable_distro(distro=first_distro)
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        # .. but a different distro should
        self.abort_recipe_with_stable_distro()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))

class TestJob(unittest.TestCase):

    def test_cc_property(self):
        session.begin()
        try:
            job = data_setup.create_job()
            session.flush()
            session.execute(job_cc_table.insert(values={'job_id': job.id,
                    'email_address': 'person@nowhere.example.com'}))
            session.refresh(job)
            self.assertEquals(job.cc, ['person@nowhere.example.com'])

            job.cc.append('korolev@nauk.su')
            session.flush()
            self.assertEquals(JobCc.query().filter_by(job_id=job.id).count(), 2)
        finally:
            session.rollback()

class TestJobCompletionNotification(unittest.TestCase):

    def setUp(self):
        self.mail_capture = MailCaptureThread()
        self.mail_capture.start()

    def tearDown(self):
        self.mail_capture.stop()

    def test_job_owner_is_notified(self):
        self.job_owner = data_setup.create_user()
        self.job = data_setup.create_job(owner=self.job_owner)
        session.flush()
        data_setup.mark_job_complete(self.job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([self.job_owner.email_address], rcpts)
        self.assertEqual(self.job_owner.email_address, msg['To'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

    def test_job_cc_list_is_notified(self):
        self.job_owner = data_setup.create_user()
        self.job = data_setup.create_job(owner=self.job_owner,
                cc=[u'dan@example.com', u'ray@example.com'])
        session.flush()
        data_setup.mark_job_complete(self.job)

        self.assertEqual(len(self.mail_capture.captured_mails), 1)
        sender, rcpts, raw_msg = self.mail_capture.captured_mails[0]
        msg = email.message_from_string(raw_msg)
        self.assertEqual([self.job_owner.email_address, 'dan@example.com',
                'ray@example.com'], rcpts)
        self.assertEqual(self.job_owner.email_address, msg['To'])
        self.assertEqual('dan@example.com, ray@example.com', msg['Cc'])
        self.assert_('[Beaker Job Completion]' in msg['Subject'])

if __name__ == '__main__':
    unittest.main()
