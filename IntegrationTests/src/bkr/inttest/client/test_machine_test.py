
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest2 as unittest
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.inttest.client import run_client
from bkr.server.model import Job, Arch, ExcludeOSMajor, OSMajor, SystemStatus

class MachineTestTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        data_setup.create_task(name=u'/distribution/inventory')
        self.distro = data_setup.create_distro(tags=[u'STABLE'])
        data_setup.create_distro_tree(distro=self.distro)

    def test_machine_test(self):
        out = run_client(['bkr', 'machine-test', '--inventory',
                '--machine', self.system.fqdn, '--arch', 'i386',
                '--family', self.distro.osversion.osmajor.osmajor])
        self.assert_(out.startswith('Submitted:'), out)

        with session.begin():
            new_job = Job.query.order_by(Job.id.desc()).first()
            self.assertEqual(new_job.whiteboard, u'Test '+ self.system.fqdn)
            tasks = new_job.recipesets[0].recipes[0].tasks
            self.assertEqual(len(tasks), 2)
            self.assertEqual(tasks[0].name, u'/distribution/install')
            self.assertEqual(tasks[1].name, u'/distribution/inventory')

        #https://bugzilla.redhat.com/show_bug.cgi?id=893878
        try:
            out = run_client(['bkr', 'machine-test','--machine', 
                              self.system.fqdn, '--tag','aTAG'])
        except Exception as ex:
            self.assertEqual(ex.stderr_output.rstrip('\n'), \
                                 'Could not find an appropriate distro to provision system with.')

    # https://bugzilla.redhat.com/show_bug.cgi?id=876752
    def test_filters_out_excluded_families(self):
        with session.begin():
            rhel3_i386 = data_setup.create_distro_tree(
                    osmajor=u'RedHatEnterpriseLinux3',
                    arch=u'i386', distro_tags=[u'STABLE'])
            rhel3_x86_64 = data_setup.create_distro_tree(
                    osmajor=u'RedHatEnterpriseLinux3',
                    arch=u'x86_64', distro_tags=[u'STABLE'])
            rhel4_i386 = data_setup.create_distro_tree(
                    osmajor=u'RedHatEnterpriseLinux4',
                    arch=u'i386', distro_tags=[u'STABLE'])
            rhel4_x86_64 = data_setup.create_distro_tree(
                    osmajor=u'RedHatEnterpriseLinux4',
                    arch=u'x86_64', distro_tags=[u'STABLE'])
            # system with RHEL4 i386 and RHEL3 x86_64 excluded
            system = data_setup.create_system(arch=u'i386')
            system.arch.append(Arch.by_name(u'x86_64'))
            system.excluded_osmajor.extend([
                ExcludeOSMajor(arch=Arch.by_name(u'i386'),
                    osmajor=OSMajor.by_name(u'RedHatEnterpriseLinux4')),
                ExcludeOSMajor(arch=Arch.by_name(u'x86_64'),
                    osmajor=OSMajor.by_name(u'RedHatEnterpriseLinux3')),
            ])
        out = run_client(['bkr', 'machine-test', '--machine', system.fqdn])
        self.assert_(out.startswith('Submitted:'), out)
        with session.begin():
            new_job = Job.query.order_by(Job.id.desc()).first()
            distro_trees = [recipe.distro_tree for recipe in new_job.all_recipes]
            self.assert_(rhel3_i386 in distro_trees, distro_trees)
            self.assert_(rhel3_x86_64 not in distro_trees, distro_trees)
            self.assert_(rhel4_i386 not in distro_trees, distro_trees)
            self.assert_(rhel4_x86_64 in distro_trees, distro_trees)

    def test_ignore_system_status(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system = data_setup.create_system(lab_controller=lc,
                                               status=SystemStatus.broken)
            distro_tree = data_setup.create_distro_tree(osmajor=u'RedHatEnterpriseLinux6',
                                                        lab_controllers=[lc],
                                                        distro_tags=[u'STABLE'])
        out = run_client(['bkr', 'machine-test', '--inventory',
                          '--debug',
                          '--machine', system.fqdn,
                          '--arch', 'i386',
                          '--ignore-system-status',
                          '--family', distro_tree.distro.osversion.osmajor.osmajor])
        self.assertIn('<hostRequires force="%s"/>' % system.fqdn,
                      out)
