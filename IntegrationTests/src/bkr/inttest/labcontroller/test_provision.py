
import time
from turbogears.database import session
from bkr.server.model import LabController, PowerType, CommandStatus
from bkr.labcontroller.config import get_conf
from bkr.inttest import data_setup
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.labcontroller import LabControllerTestCase

class PowerTest(LabControllerTestCase):

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
            lc = LabController.by_name(self.get_lc_fqdn())
            system = data_setup.create_system(lab_controller=lc)
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_id = power_sleep
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
        def _commands_completed():
            with session.begin():
                session.expire_all()
                return system.command_queue[0].status == CommandStatus.completed
        wait_for_condition(_commands_completed, timeout=5 * power_sleep)
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
