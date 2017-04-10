
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client, ClientTestCase, start_client
from bkr.server.model import Job
import re

class UpdateInventoryTest(ClientTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.system1 = data_setup.create_system(arch=[u'i386', u'x86_64'])
            self.system1.lab_controller = self.lc
            self.distro_tree1 = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                              distro_tags=[u'RELEASED'],
                                                              lab_controllers=[self.lc])
    def test_update_inventory(self):
        out = run_client(['bkr', 'update-inventory', self.system1.fqdn])
        self.assertTrue(out.startswith('Submitted:'))

    def test_update_inventory_dryrun(self):
        # old job count
        with session.begin():
            c1 = Job.query.count()
        out = run_client(['bkr', 'update-inventory', '--dryrun', self.system1.fqdn])
        self.assertFalse(out)
        with session.begin():
            session.flush()
            c2 = Job.query.count()
        # Make sure no new jobs was submitted
        self.assertEquals(c1, c2)

    def test_update_inventory_dryrun_with_update_job_already_submitted(self):
        '''
        Test if we can run the command 'bkr update-inventory --dry-run'
        without the sever giving us an error if there is already an
        inventory job running on the server.
        '''
        out = run_client(['bkr', 'update-inventory', self.system1.fqdn])
        self.assertTrue(out)
        # old job count
        with session.begin():
            c1 = Job.query.count()
        out = run_client(['bkr', 'update-inventory', '--dryrun',
                          self.system1.fqdn])
        self.assertFalse(out)
        with session.begin():
            session.flush()
            c2 = Job.query.count()
        # Make sure no new jobs were submitted
        self.assertEquals(c1, c2)

    def test_update_inventory_xml(self):
        out = run_client(['bkr', 'update-inventory', '--prettyxml', self.system1.fqdn])
        self.assertIn('<hostRequires force="%s"/>' % self.system1.fqdn,
                      out)
        self.assertIn('<task name="/distribution/inventory" role="STANDALONE"/>',
                      out)

    def test_update_inventory_wait(self):
        args = ['bkr', 'update-inventory',
                '--wait', self.system1.fqdn]
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
        self.assertEquals(returncode, 1)

