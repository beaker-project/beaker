
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.client import run_client, ClientError, ClientTestCase
from bkr.server.model import session
from bkr.inttest import data_setup
from bkr.inttest.assertions import assert_datetime_within
import datetime


class WatchdogExtend(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe)

    def test_invalid_options(self):

        try:
            run_client(['bkr','watchdog-extend'])
            self.fail('Must fail')
        except ClientError as e:
            self.assert_('Please either specify one or more <taskspec> arguments or system FQDNs' in e.stderr_output)

        try:
            run_client(['bkr','watchdog-extend', '--by=ABC'])
            self.fail('Must fail')
        except ClientError as e:
            self.assert_("invalid integer value: 'ABC'" in e.stderr_output)

    def test_invalid_taskspec(self):
        try:
            run_client(['bkr','watchdog-extend', 'J:123'])
            self.fail('Must fail')
        except ClientError as e:
            self.assert_('Taskspec type must be one of [R, T]' in e.stderr_output)

    def test_nonexistent_watchdog(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_complete(recipe)
        try:
            run_client(['bkr', 'watchdog-extend', recipe.t_id])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('No watchdog exists for recipe %s' % recipe.id,
                           e.stderr_output)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1206700
    def test_watchdog_extend_by_fqdn(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)
            recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([recipe ])
            data_setup.mark_recipe_running(recipe , system=system)

        run_client(['bkr','watchdog-extend', '--by=600', system.fqdn])

        with session.begin():
            session.expire_all()
            assert_datetime_within(recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))
        # nonexistent fqdn
        try:
            run_client(['bkr', 'watchdog-extend', 'ireallydontexistblah.test.fqdn'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('Cannot find any recipe running on ireallydontexistblah.test.fqdn', e.stderr_output)

    def test_watchdog_extend_by_recipe(self):
        run_client(['bkr','watchdog-extend', '--by=600', self.recipe.t_id])
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))
        # nonexistent recipe
        try:
            run_client(['bkr', 'watchdog-extend', 'R:0'])
            self.fail('Must raise')
        except ClientError as e:
            self.assertIn('0 is not a valid Recipe id', e.stderr_output)

    def test_watchdog_extend_by_recipe_task(self):
        run_client(['bkr','watchdog-extend', '--by=600', self.recipe.tasks[0].t_id])
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))

    def test_watchdog_extend_by_plain_task_id(self):
        run_client(['bkr','watchdog-extend', '--by=600', str(self.recipe.tasks[0].id)])
        with session.begin():
            session.expire_all()
            assert_datetime_within(self.recipe.watchdog.kill_time,
                    tolerance=datetime.timedelta(seconds=10),
                    reference=datetime.datetime.utcnow() + datetime.timedelta(seconds=600))
