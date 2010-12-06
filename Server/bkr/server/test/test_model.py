import sys
import time
import unittest
import email
from turbogears.database import session
from bkr.server.model import System, SystemStatus, SystemActivity, TaskStatus, \
        SystemType, Job, JobCc, Key, Key_Value_Int, Key_Value_String, \
        job_cc_table
from bkr.server.test import data_setup

class TestSystem(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_create_system_params(self):
        new_system = System(fqdn=u'test_fqdn', contact=u'test@email.com',
                            location=u'Brisbane', model=u'Proliant', serial=u'4534534',
                            vendor=u'Dell', type=SystemType.by_name(u'Machine'),
                            status=SystemStatus.by_name(u'Automated'))
        session.flush()
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
        session.flush()
        self.assertEquals(system.user, user)

    def test_remove_user_from_system(self):
        user = data_setup.create_user()
        system = data_setup.create_system()
        system.user = user
        system.user = None
        session.flush()
        self.assert_(system.user is None)

class TestSystemKeyValue(unittest.TestCase):

    def setUp(self):
        session.begin()

    def tearDown(self):
        session.rollback()

    def test_removing_key_type_cascades_to_key_value(self):
        # https://bugzilla.redhat.com/show_bug.cgi?id=647566
        string_key_type = Key(u'COLOUR', numeric=False)
        int_key_type = Key(u'FAIRIES', numeric=True)
        system = data_setup.create_system()
        system.key_values_string.append(
                Key_Value_String(string_key_type, u'pretty pink'))
        system.key_values_int.append(Key_Value_Int(int_key_type, 9000))
        session.flush()

        session.delete(string_key_type)
        session.delete(int_key_type)
        session.flush()

        session.clear()
        reloaded_system = session.get(System, system.id)
        self.assertEqual(reloaded_system.key_values_string, [])
        self.assertEqual(reloaded_system.key_values_int, [])

class TestBrokenSystemDetection(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=637260
    # The 1-second sleeps here are so that the various timestamps
    # don't end up within the same second

    def setUp(self):
        self.system = data_setup.create_system()
        self.system.status = SystemStatus.by_name(u'Automated')
        data_setup.create_completed_job(system=self.system)
        session.flush()
        time.sleep(1)

    def abort_recipe(self, distro=None):
        if distro is None:
            distro = data_setup.create_distro()
            distro.tags.append(u'RELEASED')
        recipe = data_setup.create_recipe(distro=distro)
        data_setup.create_job_for_recipes([recipe])
        recipe.system = self.system
        recipe.tasks[0].status = TaskStatus.by_name(u'Running')
        recipe.update_status()
        session.flush()
        recipe.abort()

    def test_multiple_suspicious_aborts_triggers_broken_system(self):
        # first aborted recipe shouldn't trigger it
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        # another recipe with a different stable distro *should* trigger it
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))

    def test_status_change_is_respected(self):
        # two aborted recipes should trigger it...
        self.abort_recipe()
        self.abort_recipe()
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
        self.abort_recipe()
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken')) # not broken! yet
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken')) # now it is

    def test_counts_distinct_stable_distros(self):
        first_distro = data_setup.create_distro()
        first_distro.tags.append(u'RELEASED')
        # two aborted recipes for the same distro shouldn't trigger it
        self.abort_recipe(distro=first_distro)
        self.abort_recipe(distro=first_distro)
        self.assertNotEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        # .. but a different distro should
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))

    def test_updates_modified_date(self):
        orig_date_modified = self.system.date_modified
        self.abort_recipe()
        self.abort_recipe()
        self.assertEqual(self.system.status, SystemStatus.by_name(u'Broken'))
        self.assert_(self.system.date_modified > orig_date_modified)

class TestJob(unittest.TestCase):

    def test_cc_property(self):
        session.begin()
        try:
            job = data_setup.create_job()
            session.flush()
            session.execute(job_cc_table.insert(values={'job_id': job.id,
                    'email_address': u'person@nowhere.example.com'}))
            session.refresh(job)
            self.assertEquals(job.cc, ['person@nowhere.example.com'])

            job.cc.append(u'korolev@nauk.su')
            session.flush()
            self.assertEquals(JobCc.query().filter_by(job_id=job.id).count(), 2)
        finally:
            session.rollback()

if __name__ == '__main__':
    unittest.main()
