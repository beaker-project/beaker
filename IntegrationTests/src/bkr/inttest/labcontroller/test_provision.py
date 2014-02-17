
import time
from turbogears.database import session
from nose.plugins.skip import SkipTest
from bkr.server.model import LabController, PowerType, CommandStatus
from bkr.labcontroller.config import get_conf
from bkr.inttest import data_setup
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.labcontroller import LabControllerTestCase, processes, \
        daemons_running_externally

def wait_for_commands_completed(system, timeout):
    def _commands_completed():
        with session.begin():
            session.expire_all()
            return system.command_queue[0].status == CommandStatus.completed
    wait_for_condition(_commands_completed, timeout=timeout)

class PowerTest(LabControllerTestCase):

    # BEWARE IF USING 'dummy' POWER TYPE:
    # The 'dummy' power script sleeps for $power_id seconds, therefore tests 
    # must ensure they set power_id to a sensible value ('0' or '' unless the 
    # test demands a longer delay).

    # https://bugzilla.redhat.com/show_bug.cgi?id=951309
    def test_power_commands_are_not_run_twice(self):
        # We will make the dummy power script sleep for this long:
        power_sleep = 4
        # To reproduce this bug, we need to queue up three commands for the 
        # same system (so they are run in sequence by beaker-provision), where 
        # the commands take enough time that the second one will still be 
        # running on the next iteration of the polling loop. The third command 
        # will be run twice.
        assert power_sleep < get_conf().get('SLEEP_TIME')
        assert 2 * power_sleep > get_conf().get('SLEEP_TIME')
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_id = power_sleep # make power script sleep
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
        wait_for_commands_completed(system, timeout=5 * power_sleep)
        with session.begin():
            session.expire_all()
            self.assertEquals(system.command_queue[0].status, CommandStatus.completed)
            self.assertEquals(system.command_queue[1].status, CommandStatus.completed)
            self.assertEquals(system.command_queue[2].status, CommandStatus.completed)
            # The bug manifests as two "Completed" records for the power 
            # command which ran twice
            self.assertEquals(system.dyn_activity
                    .filter_by(field_name=u'Power', new_value=u'Completed')
                    .count(), 3)

    def test_blank_power_passwords(self):
        if daemons_running_externally():
            raise SkipTest('cannot examine logs of remote beaker-provision')
        provision_process, = [p for p in processes if p.name == 'beaker-provision']
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = data_setup.create_system(lab_controller=self.get_lc())
                system.power.address = None
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_id = u'' # make power script not sleep
                system.power.power_passwd = None
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_completed(system, timeout=2 * get_conf().get('SLEEP_TIME'))
        finally:
            provision_output = provision_process.finish_output_capture()
        # The None type is passed in from the db. Later in the code it is converted
        # to the empty string, as it should be.
        self.assertIn("'passwd': None", provision_output, provision_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=986108
    def test_power_passwords_are_not_logged(self):
        if daemons_running_externally():
            raise SkipTest('cannot examine logs of remote beaker-provision')
        provision_process, = [p for p in processes if p.name == 'beaker-provision']
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = data_setup.create_system(lab_controller=self.get_lc())
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_id = u'' # make power script not sleep
                system.power.power_passwd = u'dontleakmebro'
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_completed(system, timeout=2 * get_conf().get('SLEEP_TIME'))
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assert_('Handling command' in provision_output, provision_output)
        self.assert_('Launching power script' in provision_output, provision_output)
        self.assert_(system.power.power_passwd not in provision_output, provision_output)
