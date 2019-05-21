
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import textwrap
from turbogears.database import session
from bkr.server.model import SystemStatus, Recipe
from json import loads
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientError, ClientTestCase

try:
    unicode('')
except:
    unicode = str


class SystemStatusTest(ClientTestCase):

    def test_unknown_fqdn(self):
        try:
            run_client(['bkr', 'system-status',
                data_setup.unique_name('invalid.example%s.com')])
            self.fail('Should raise 404 from the server')
        except ClientError as e:
            self.assertIn('System not found', e.stderr_output)

    def test_reserve_with_recipe(self):
        with session.begin():
            recipe = data_setup.create_recipe()
            job = data_setup.create_job_for_recipes([recipe])
            data_setup.mark_job_running(job)
            recipe = Recipe.by_id(recipe.id)
            fqdn = recipe.resource.system.fqdn
            user = recipe.resource.system.user
            recipe.resource.system.loaned = user
            recipe.resource.system.loan_comment = u'Amy, must I jujitsu my ma?'
        system = recipe.resource.system
        # JSON output
        json_out = run_client(['bkr', 'system-status', fqdn, '--format',
            'json'])
        json_out = loads(json_out)
        current_reservation = json_out.get('current_reservation')
        self.assertEqual(current_reservation.get('user_name'),
            unicode(system.user))
        self.assertEqual(current_reservation.get('recipe_id'), '%s' % \
            system.open_reservation.recipe.id)
        self.assertEqual(json_out.get('condition'), '%s' % system.status)

        # Human friendly output
        human_out = run_client(['bkr', 'system-status', fqdn])
        expected_out = textwrap.dedent('''\
            Condition: %s
            Current reservation:
                User: %s
                Recipe ID: %s
                Start time: %s UTC
            Current loan:
                User: %s
                Comment: Amy, must I jujitsu my ma?''' % \
            (system.status, system.user, system.open_reservation.recipe.id,
            system.open_reservation.recipe.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            system.loaned))
        human_out = human_out.rstrip('\n')
        self.assertEqual(human_out, expected_out, human_out)


    def test_reserve_manually(self):
        with session.begin():
            system = data_setup.create_system(status=SystemStatus.manual)
            user = data_setup.create_user()
            system.reserve_manually(u'TESTING', user=user)
        json_out = run_client(['bkr', 'system-status', system.fqdn,
            '--format', 'json'])
        json_out = loads(json_out)
        current_reservation = json_out['current_reservation']
        self.assertEqual(current_reservation.get('user_name'), unicode(user))
        self.assertEqual(json_out.get('current_loan'), None)
        self.assertEqual(json_out.get('condition'), '%s' % SystemStatus.manual)

        # Human friendly output
        human_out = run_client(['bkr', 'system-status', system.fqdn])
        expected_out = textwrap.dedent('''\
            Condition: %s
            Current reservation:
                User: %s
            Current loan: None''' % (system.status, system.user,))
        human_out = human_out.rstrip('\n')
        self.assertEqual(human_out, expected_out, human_out)

    def test_unpopulated_status(self):
        with session.begin():
            system = data_setup.create_system(
                lab_controller=data_setup.create_labcontroller(),
                status=SystemStatus.automated)
        json_out = run_client(['bkr', 'system-status', system.fqdn,
            '--format', 'json'])
        json_out = loads(json_out)
        self.assertEqual(json_out.get('current_reservation'), None)
        self.assertEqual(json_out.get('current_loan'), None)
        self.assertEqual(json_out.get('condition'), unicode(system.status))

        # Human friendly output
        human_out = run_client(['bkr', 'system-status', system.fqdn])
        expected_out = textwrap.dedent('''\
            Condition: %s
            Current reservation: None
            Current loan: None''' % (system.status))
        human_out = human_out.rstrip('\n')
        self.assertEqual(human_out, expected_out, human_out)
