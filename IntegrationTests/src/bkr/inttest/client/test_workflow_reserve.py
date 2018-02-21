
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, start_client, ClientTestCase
from bkr.server.model import Job, SystemStatus

class WorkflowReserveTest(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system = data_setup.create_system(lab_controller=self.lc,
                                               arch=[u'aarch64'],
                                               status=SystemStatus.broken)
            self.distro_tree = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux7',
                                                        lab_controllers=[self.lc],
                                                        distro_tags=[u'STABLE'],
                                                        arch=u'aarch64')

    def test_reserve_automated_system(self):
        out = run_client(['bkr', 'workflow-reserve',
                          '--dryrun',
                          '--debug',
                          '--arch', 'aarch64',
                          '--family', 'RedHatEnterpriseLinux7'])
        self.assertIn('<reservesys/>', out)
        # just make sure no system will be reserved.
        self.assertNotIn('Submitted', out)

    def test_arch_defaults_to_x86_when_reserving_automated_system(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc)

        out = run_client(['bkr', 'workflow-reserve',
                          '--debug',
                          '--dryrun',
                          '--family', 'RedHatEnterpriseLinux7'])
        self.assertIn('<distro_arch op="=" value="x86_64"/>', out)

    def test_default_arch_when_reserving_broken_system(self):
        out = run_client(['bkr', 'workflow-reserve',
                          '--debug',
                          '--dryrun',
                          '--machine', self.system.fqdn,
                          '--family', self.distro_tree.distro.osversion.osmajor.osmajor])
        self.assertIn('<distro_arch op="=" value="aarch64"/>', out)

    def test_default_family_when_reserving_broken_system(self):
        out = run_client(['bkr', 'workflow-reserve',
                          '--debug',
                          '--dryrun',
                          '--machine', self.system.fqdn])
        self.assertIn('<distro_name op="=" value="%s"/>' % self.distro_tree.distro.name, out)

    def test_watch_job(self):
        args = ['bkr', 'workflow-reserve',
                '--machine', self.system.fqdn,
                '--family', 'RedHatEnterpriseLinux7',
                '--wait']
        proc = start_client(args)
        out = proc.stdout.readline().rstrip()
        self.assert_(out.startswith('Submitted:'), out)
        m = re.search('J:(\d+)', out)
        job_id = m.group(1)

        out = proc.stdout.readline().rstrip()

        self.assert_('Watching tasks (this may be safely interrupted)...' == out)

        with session.begin():
            job = Job.by_id(job_id)
            job.cancel()
            job.update_status()

        returncode = proc.wait()
        self.assert_(returncode == 1)
