# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import time
import logging
import pkg_resources
from turbogears.database import session
from unittest import SkipTest, TestCase
from xmlrpclib import _Method
from bkr.server.model import PowerType, CommandStatus, System, User, SystemStatus
from bkr.labcontroller.config import get_conf
from bkr.labcontroller.provision import CommandQueuePoller
from bkr.inttest import data_setup, Process
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.labcontroller import LabControllerTestCase, processes, daemons_running_externally

log = logging.getLogger(__name__)


def wait_for_commands_to_finish(system, timeout):
    def _commands_finished():
        with session.begin():
            session.expire_all()
            return system.command_queue[0].status in \
                   (CommandStatus.completed, CommandStatus.failed)

    wait_for_condition(_commands_finished, timeout=timeout)


def wait_for_command_to_finish(command, timeout):
    def _command_completed():
        with session.begin():
            session.refresh(command)
            return command.status in (CommandStatus.completed, CommandStatus.failed)

    wait_for_condition(_command_completed, timeout=timeout)


def assert_command_is_delayed(command, min_delay, timeout):
    """
    Asserts that the given command is not run for at least *min_delay* seconds,
    and also completes within *timeout* seconds after the delay has elapsed.
    """

    def _command_completed():
        with session.begin():
            session.refresh(command)
            return command.status == CommandStatus.completed

    assert not _command_completed(), 'Command should not be completed initially'
    log.info('Command %s is not completed initially', command.id)
    time.sleep(min_delay)
    assert not _command_completed(), 'Command should still not be completed after delay'
    log.info('Command %s is still not completed after delay', command.id)
    wait_for_condition(_command_completed, timeout=timeout)
    log.info('Command %s is completed', command.id)


class PowerTest(LabControllerTestCase):

    # BEWARE IF USING 'dummy' POWER TYPE:
    # The 'dummy' power script sleeps for $power_id seconds, therefore tests
    # must ensure they set power_id to a sensible value ('0' or '' unless the
    # test demands a longer delay).

    def test_power_quiescent_period(self):
        # Test that we do in fact wait for the quiescent period to pass
        # before running a command.
        # This time is needed to guarantee that we are actually waiting for
        # the quiescent period and not waiting for another poll loop:
        quiescent_period = get_conf().get('SLEEP_TIME') * 3
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            self.addCleanup(self.cleanup_system, system)
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_quiescent_period = quiescent_period
            system.power.power_id = u''  # make power script not sleep
            system.power.delay_until = None
            system.action_power(action=u'off', service=u'testdata')
            command = system.command_queue[0]
        assert_command_is_delayed(command, quiescent_period - 0.5, 10)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1079816
    def test_quiescent_period_is_obeyed_for_consecutive_commands(self):
        quiescent_period = 3
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            self.addCleanup(self.cleanup_system, system)
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_quiescent_period = quiescent_period
            system.power.power_id = u''  # make power script not sleep
            system.power.delay_until = None
            system.action_power(action=u'on', service=u'testdata')
            system.action_power(action=u'on', service=u'testdata')
            system.action_power(action=u'on', service=u'testdata')
            commands = system.command_queue[:3]
        assert_command_is_delayed(commands[2], quiescent_period - 0.5, 10)
        assert_command_is_delayed(commands[1], quiescent_period - 0.5, 10)
        assert_command_is_delayed(commands[0], quiescent_period - 0.5, 10)

    def test_power_quiescent_period_statefulness_not_elapsed(self):
        if daemons_running_externally():
            raise SkipTest('cannot examine logs of remote beaker-provision')
        provision_process, = [p for p in processes if p.name == \
                              'beaker-provision']
        # Initial lookup of this system will reveal no state, so will delay
        # for the whole quiescent period
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = data_setup.create_system(lab_controller=self.get_lc())
                self.addCleanup(self.cleanup_system, system)
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_quiescent_period = 1
                system.power.power_id = u''  # make power script not sleep
                system.power.delay_until = None
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=10)
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assertIn('Entering quiescent period, delaying 1 seconds for '
                      'command %s' % system.command_queue[0].id, provision_output)
        # Increase the quiescent period, to ensure we enter it
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = System.by_id(system.id, User.by_user_name(u'admin'))
                system.power.power_quiescent_period = 10
                system.action_power(action=u'on', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=15)
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assertIn('Entering quiescent period', provision_output)

    def test_power_quiescent_period_statefulness_elapsed(self):
        if daemons_running_externally():
            raise SkipTest('cannot examine logs of remote beaker-provision')
        provision_process, = [p for p in processes if p.name == \
                              'beaker-provision']
        # Initial lookup of this system will reveal no state, so will delay
        # for the whole quiescent period
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = data_setup.create_system(lab_controller=self.get_lc())
                self.addCleanup(self.cleanup_system, system)
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_quiescent_period = 1
                system.power.power_id = u''  # make power script not sleep
                system.power.delay_until = None
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=10)
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assertIn('Entering quiescent period, delaying 1 seconds for '
                      'command %s' % system.command_queue[0].id, provision_output)
        # This guarantees our quiescent period has elapsed and be ignored
        time.sleep(1)
        try:
            provision_process.start_output_capture()
            with session.begin():
                system = System.by_id(system.id, User.by_user_name(u'admin'))
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=10)
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assertNotIn('Entering queiscent period', provision_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1083648
    def test_quiescent_period_only_applies_between_power_commands(self):
        # The purpose of the quiescent period is for power supplies with
        # peculiar characteristics that need time to discharge or similar.
        # But the quiescent period should not count any other commands like
        # clear_logs or configure_netboot, because those are not touching the
        # power supply.
        loop_interval = get_conf().get('SLEEP_TIME')
        quiescent_period = loop_interval * 3.0
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            self.addCleanup(self.cleanup_system, system)
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_quiescent_period = quiescent_period
            system.power.power_id = u''  # make power script not sleep
            system.action_power(action=u'off', service=u'testdata')
            system.enqueue_command(action=u'clear_netboot', service=u'testdata')
            commands = system.command_queue[:2]
        assert_command_is_delayed(commands[1], quiescent_period - 0.5, timeout=2 * loop_interval)
        wait_for_command_to_finish(commands[0], timeout=2 * loop_interval)
        time.sleep(quiescent_period)
        # Now there should be no delays because the quiescent period has
        # already elapsed since the 'off' command above.
        with session.begin():
            system.enqueue_command(action=u'clear_logs', service=u'testdata')
            system.action_power(action=u'on', service=u'testdata')
            commands = system.command_queue[:2]
        wait_for_command_to_finish(commands[1], timeout=2 * loop_interval)
        wait_for_command_to_finish(commands[0], timeout=2 * loop_interval)

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
            self.addCleanup(self.cleanup_system, system)
            system.power.power_quiescent_period = 0
            system.power.power_type = PowerType.lazy_create(name=u'dummy')
            system.power.power_id = power_sleep  # make power script sleep
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
            system.action_power(action=u'off', service=u'testdata')
        wait_for_commands_to_finish(system, timeout=5 * power_sleep)
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
                self.addCleanup(self.cleanup_system, system)
                system.power.address = None
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_id = u''  # make power script not sleep
                system.power.power_passwd = None
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=2 * get_conf().get(u'SLEEP_TIME'))
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
                self.addCleanup(self.cleanup_system, system)
                system.power.power_type = PowerType.lazy_create(name=u'dummy')
                system.power.power_id = u''  # make power script not sleep
                system.power.power_passwd = u'dontleakmebro'
                system.action_power(action=u'off', service=u'testdata')
            wait_for_commands_to_finish(system, timeout=2 * get_conf().get('SLEEP_TIME'))
        finally:
            provision_output = provision_process.finish_output_capture()
        self.assert_('Handling command' in provision_output, provision_output)
        self.assert_('Launching power script' in provision_output, provision_output)
        self.assert_(system.power.power_passwd not in provision_output, provision_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1358063
    def test_power_passwords_are_not_reported_in_failure_message(self):
        with session.begin():
            system = data_setup.create_system(lab_controller=self.get_lc())
            self.addCleanup(self.cleanup_system, system)
            system.power.power_type = PowerType.lazy_create(name=u'testing-bz1358063')
            system.power.power_passwd = u'dontleakmebro'
            system.power.quiescent_period = 0
            system.action_power(action=u'off', service=u'testdata')
        timeout = (2 * get_conf().get('SLEEP_TIME') +
                   get_conf().get('POWER_ATTEMPTS') * 2 ** get_conf().get('POWER_ATTEMPTS'))
        wait_for_commands_to_finish(system, timeout=timeout)
        self.assertEqual(system.command_queue[0].status, CommandStatus.failed)
        self.assertIn(u'failed after 2 attempts with exit status 1:\npassword is ********',
                      system.command_queue[0].error_message)


class ConfigureNetbootTest(LabControllerTestCase):

    @classmethod
    def setUpClass(cls):
        cls.distro_server = Process('http_server.py', args=[sys.executable,
                                                            pkg_resources.resource_filename(
                                                                'bkr.inttest', 'http_server.py'),
                                                            '--base', '/notexist'],
                                    listen_port=19998)
        cls.distro_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.distro_server.stop()

    # https://bugzilla.redhat.com/show_bug.cgi?id=1094553
    def test_timeout_is_enforced_for_fetching_images(self):
        with session.begin():
            lc = self.get_lc()
            system = data_setup.create_system(arch=u'x86_64', lab_controller=lc)
            self.addCleanup(self.cleanup_system, system)
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                                                        lab_controllers=[lc],
                                                        # /slow/600 means the response will be delayed 10 minutes
                                                        urls=[u'http://localhost:19998/slow/600/'])
            installation = distro_tree.create_installation_from_tree()
            installation.tree_url = distro_tree.url_in_lab(lab_controller=lc)
            installation.kernel_options = u''
            system.configure_netboot(installation=installation, service=u'testdata')
        wait_for_commands_to_finish(system, timeout=(2 * get_conf().get('SLEEP_TIME')
                                                     + get_conf().get('IMAGE_FETCH_TIMEOUT')))
        self.assertEquals(system.command_queue[0].action, u'configure_netboot')
        self.assertEquals(system.command_queue[0].status, CommandStatus.failed)
        self.assertIn(u'timed out', system.command_queue[0].error_message)

    # https://bugzilla.redhat.com/show_bug.cgi?id=874387
    def test_system_not_marked_broken_for_missing_distro_tree_images(self):
        with session.begin():
            lc = self.get_lc()
            system = data_setup.create_system(arch=u'x86_64', lab_controller=lc,
                                              status=SystemStatus.automated)
            self.addCleanup(self.cleanup_system, system)
            distro_tree = data_setup.create_distro_tree(arch=u'x86_64',
                                                        lab_controllers=[lc],
                                                        urls=[u'http://localhost:19998/error/404/'])
            installation = distro_tree.create_installation_from_tree()
            installation.tree_url = distro_tree.url_in_lab(lab_controller=lc)
            installation.kernel_options = u''
            system.configure_netboot(installation=installation, service=u'testdata')
        wait_for_commands_to_finish(system, timeout=(2 * get_conf().get('SLEEP_TIME')))
        self.assertEquals(system.command_queue[0].action, u'configure_netboot')
        self.assertEquals(system.command_queue[0].status, CommandStatus.failed)
        self.assertEquals(system.status, SystemStatus.automated)


class FakeHub(object):
    """
    Implements a fake xmlrpc hub for purposes
    of stubbing out responses
    """

    def __init__(self, testcase):
        self.testcase = testcase
        self.aborted_commands = []

    def assert_commands_aborted(self):
        self.testcase.assertListEqual([3, 4, 5], self.aborted_commands)

    def get_queued_command_details(self, args):
        return [{'id': 1}, {'id': 2}]

    def get_running_command_ids(self, args):
        return [1, 2, 3, 4, 5]

    def mark_command_aborted(self, args):
        command_id = args[0]
        self.testcase.assertIn(command_id, [3, 4, 5])
        self.aborted_commands.append(command_id)

    def __request(self, method, params):
        methodname = method.split(".").pop()
        return getattr(self, methodname)(params)

    def __getattr__(self, name):
        return _Method(self.__request, name)


class ProvisionXmlrpcTest(TestCase):
    def test_clear_orphaned_commands(self):
        testhub = FakeHub(self)
        initial_commands = {1: {'id': 1},
                            2: {'id': 2}}
        poller = CommandQueuePoller(conf=None, hub=testhub)
        poller.commands = initial_commands
        poller.poll()
        # Verify that the poller called abort on the three unknown commands
        testhub.assert_commands_aborted()
        # For completeness, assert poller state unchanged after poll()
        self.assertDictEqual(initial_commands, poller.commands)
        self.assertDictEqual({}, poller.greenlets)
        self.assertDictEqual({}, poller.last_command_datetime)
