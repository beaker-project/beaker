
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.inttest.client import run_client, ClientTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import session, Arch, Job

class HarnessTest(ClientTestCase):

    @with_transaction
    def setUp(self):
        i386 = Arch.by_name(u'i386')
        x86_64 = Arch.by_name(u'x86_64')
        self.distro = data_setup.create_distro(osmajor=u'MyAwesomeLinux',
                                               tags=[u'STABLE'],
                                               arches=[i386, x86_64])
        data_setup.create_distro_tree(distro=self.distro,
                                      arch=u'i386')
        data_setup.create_distro_tree(distro=self.distro,
                                      arch=u'x86_64')

    def test_submit_job(self):
        out = run_client(['bkr', 'harness-test',
                          '--debug',
                          '--prettyxml',
                          '--family', self.distro.osversion.osmajor.osmajor])
        self.assertIn('<distro_arch op="=" value="i386"/>', out)
        self.assertIn('<distro_arch op="=" value="x86_64"/>', out)

    def test_machine_hostfilter(self):
        out = run_client(['bkr', 'harness-test',
                          '--debug',
                          '--prettyxml',
                          '--family', self.distro.osversion.osmajor.osmajor,
                          '--machine', 'test.system',
                      ])
        self.assertIn('<hostname op="=" value="test.system"/>',
                      out)

    def test_no_requested_tasks(self):
        # If you don't request any tasks (by passing the --task option)
        # each recipe should contain only the install checking task
        # and nothing more.
        with session.begin():
            data_setup.create_distro_tree(osmajor=u'Fedorarawhide')
            data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux7')
        out = run_client(['bkr', 'harness-test'])
        self.assertIn("Submitted:", out)
        with session.begin():
            new_job = Job.query.order_by(Job.id.desc()).first()
            # There will be one recipe per OS major that exists in the database,
            # which is potentially a large number left from earlier tests.
            # What we care about is that every recipe must have one task,
            # /distribution/check-install
            self.assertGreater(len(new_job.recipesets), 1)
            for recipe in new_job.all_recipes:
                self.assertEqual(len(recipe.tasks), 1)
                if recipe.installation.osmajor == 'Fedorarawhide':
                    self.assertEqual(recipe.tasks[0].name, '/distribution/check-install')
                if recipe.installation.osmajor == 'RedHatEnterpriseLinux7':
                    self.assertEqual(recipe.tasks[0].name, '/distribution/check-install')
