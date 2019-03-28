
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import datetime
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase


class WatchdogShowTest(ClientTestCase):

    def test_watchdog_show_running_task(self):
        with session.begin():
            r1 = data_setup.create_recipe()
            data_setup.create_job_for_recipes([r1])
            data_setup.mark_recipe_running(r1)
            session.flush()
            t1 = r1.tasks[0]
            t1.watchdog.kill_time = datetime.datetime.utcnow() + \
                datetime.timedelta(seconds=99)
        out = run_client(['bkr', 'watchdog-show', str(t1.id)])
        # Let's just check it is somewhere between 10-99
        self.assertTrue(re.match('%s: \d\d\\n' % t1.id, out))

    def test_watchdog_show_non_running_task(self):
        with session.begin():
            r1 = data_setup.create_recipe()
            data_setup.create_job_for_recipes([r1])
        out = run_client(['bkr', 'watchdog-show', '%s' % r1.tasks[0].id])
        self.assertEquals(out, '%s: N/A\n' % r1.tasks[0].id, out)
