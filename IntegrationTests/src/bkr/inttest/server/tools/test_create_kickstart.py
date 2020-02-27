
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import tempfile
import shutil
import subprocess
from cStringIO import StringIO
from turbogears.database import session
from bkr.common import __version__
from bkr.inttest import data_setup, DatabaseTestCase
from bkr.inttest.kickstart_helpers import create_rhel62, create_rhel62_server_x86_64, \
    create_lab_controller, create_x86_64_automated, compare_expected, \
    jinja_choice_loader, create_user
from bkr.inttest.server.tools import run_command, CommandError
from bkr.server.tools import create_kickstart
from bkr.server.kickstart import template_env
from bkr.server.model import Task, User, Recipe, Provision, Arch, OSMajorInstallOptions

class CreateKickstartTest(DatabaseTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        admin_user = User.by_user_name(data_setup.ADMIN_USER)
        if getattr(self,'recipe_id', None):
            with session.begin():
                recipe = Recipe.by_id(self.recipe_id)
                if recipe.resource.system.open_reservation:
                    recipe.resource.release()

    def _create_recipe(self, system=None):
        with session.begin():
            install_task = Task.by_name(u'/distribution/check-install')
            reserve_task = Task.by_name(u'/distribution/reservesys')
            lc = create_lab_controller()
            rhel62_server_x86_64 = create_rhel62_server_x86_64(lab_controller=lc)
            if not system:
                system = create_x86_64_automated(lc)
            recipe = data_setup.create_recipe(distro_tree=rhel62_server_x86_64, task_list=[install_task, reserve_task])
            data_setup.create_job_for_recipes([recipe], owner=create_user(), whiteboard=u'')
            data_setup.mark_recipe_complete(recipe, system=system)
        self.recipe_id = recipe.id
        return recipe

    def _create_recipe_with_user_defined_distro(self, **kwargs):
        with session.begin():
            install_task = Task.by_name(u'/distribution/check-install')
            reserve_task = Task.by_name(u'/distribution/reservesys')
            lc = create_lab_controller()
            system = create_x86_64_automated(lc)
            recipe = data_setup.create_recipe(custom_distro=True, osmajor=kwargs['osmajor'],
                                              task_list=[install_task, reserve_task]) if \
                'osmajor' in kwargs else data_setup.create_recipe(custom_distro=True, task_list=[install_task, reserve_task])
            data_setup.create_job_for_recipes([recipe], owner=create_user(), whiteboard=u'')
            data_setup.mark_recipe_complete(recipe, system=system)
        self.recipe_id = recipe.id
        return recipe

    def _create_i386_distro(self, lc):
        i386_distro = data_setup.create_distro(
            osmajor=u'RedHatEnterpriseLinux6', arches=[Arch.by_name(u'i386')])
        i386_distro_tree = data_setup.create_distro_tree(distro=i386_distro,
            lab_controllers=[lc],
            urls=[u'http://lab.test-kickstart.example.com/distros/RHEL-6.3/'
                u'Workstation/i386/os/'],
            variant=u'Workstation')
        return i386_distro

    def _run_create_kickstart(self, args):
        return run_command('create_kickstart.py', 'beaker-create-kickstart', args)

    def test_version(self):
        out = run_command('create_kickstart.py', 'beaker-create-kickstart', ['--version'])
        self.assertEquals(out.strip(), __version__)

    def test_nonexistent_recipe_id(self):
        try:
            self._run_create_kickstart(['--recipe-id', '0'])
            self.fail('Should raise an exception when passed an invalid recipe'
                ' id')
        except CommandError as e:
            self.assertIn("RuntimeError: Recipe id '0' does not exist",
                    e.stderr_output)

    def test_create_kickstart_of_unknown_osmajor_does_not_fail(self):
        system = data_setup.create_system()
        recipe = self._create_recipe_with_user_defined_distro(osmajor='SomeRandomLinux1')
        self.assertIsNotNone(self._run_create_kickstart(['--recipe-id', str(recipe.id),
                '--system', system.fqdn]))

    def test_nonexistent_system_fqdn(self):
        recipe = self._create_recipe()
        try:
            self._run_create_kickstart(['--recipe-id', str(recipe.id),
                '--system', 'dsaffds124143g'])
            self.fail('Should raise an exception when passed an invalid system'
                ' fqdn')
        except CommandError as e:
            self.assertIn("RuntimeError: System 'dsaffds124143g' does not "
                "exist", e.stderr_output)

    def test_nonexistent_distro_tree_id(self):
        recipe = self._create_recipe()
        with session.begin():
            system = data_setup.create_system()
        try:
            self._run_create_kickstart(['--recipe-id', str(recipe.id),
                '--system', system.fqdn, '--distro-tree-id', '0'])
            self.fail('Should raise an exception when passed an invalid distro'
                ' tree id')
        except CommandError as e:
            self.assertIn("RuntimeError: Distro tree id '0' does not exist",
                e.stderr_output)

    def test_snippet_dir(self):
        recipe = self._create_recipe()
        session.expire_all()
        template_dir = tempfile.mkdtemp()
        try:
            snippet_dir = os.path.join(template_dir, 'snippets')
            os.mkdir(snippet_dir)
            with open('%s/timezone' % snippet_dir, 'w') as file:
                file.write("timezone Africa/Juba\n")
            output = self._run_create_kickstart(['--template-dir',
                template_dir, '--recipe-id', str(recipe.id)])
        finally:
            shutil.rmtree(snippet_dir)

        self.assertIn('timezone Africa/Juba', output.splitlines(),
            output)

        # Assert that snippets are still being pulled from the normal
        # places as well
        self.assertIn('nfs --server lab.test-kickstart.invalid --dir '
            '/distros/RHEL-6.2/Server/x86_64/os/', output.splitlines(),
            output)

    def test_ks_meta_koptions_post(self):
        recipe = self._create_recipe()
        session.expire_all()
        output = self._run_create_kickstart(['--ks-meta', 'method=http',
            '--kernel-options-post', "console=ttyS0,9600n8 pci=nomsi",
            '--recipe-id', str(recipe.id)])
        session.expire_all()
        self.assertIn('url --url=http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/x86_64/os/',
            output.splitlines(),
            output)
        self.assertIn('bootloader --location=mbr --append="console=ttyS0,9600n8 pci=nomsi"',
            output.splitlines(),
            output)

    def test_rhel6_defaults_recipe(self):
        recipe = self._create_recipe()
        session.expire_all()
        generated_ks = self._run_create_kickstart(['--recipe-id', str(recipe.id)])
        compare_expected('RedHatEnterpriseLinux6-scheduler-defaults-beaker-create-kickstart',
            recipe.id, generated_ks)

    def test_rhel6_defaults_no_recipe(self):
        with session.begin():
            lc = create_lab_controller()
            system = create_x86_64_automated(lc)
            self.rhel62_server_x86_64 = create_rhel62_server_x86_64(lab_controller=lc)
            user = create_user()
        session.expire_all()
        distro_tree_id = self.rhel62_server_x86_64.id
        generated_ks = self._run_create_kickstart(['--distro-tree-id',
            str(distro_tree_id), '--system', system.fqdn, '--user', user.user_name])
        compare_expected('RedHatEnterpriseLinux6-manual-defaults-beaker-create-kickstart', None,
               generated_ks)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1058156
    def test_system_overrides_recipe(self):
        with session.begin():
            lc = create_lab_controller()
            system1 = data_setup.create_system(lab_controller=lc,
                arch='x86_64')
            system2 = data_setup.create_system(lab_controller=lc,
                arch='x86_64')
            system1.provisions[system1.arch[0]] = Provision(arch=system1.arch[0],
                kernel_options_post='adalovelace')
            system2.provisions[system2.arch[0]] = Provision(arch=system2.arch[0],
                kernel_options_post='phonykerneloption')

        recipe = self._create_recipe(system1)
        kickstart = self._run_create_kickstart(['--recipe-id', str(recipe.id),
                                                '--system', system2.fqdn,])

        self.assertIn('phonykerneloption', kickstart)
        self.assertIn(system2.fqdn, kickstart)
        self.assertNotIn('adalovelace', kickstart)
        self.assertNotIn(system1.fqdn, kickstart)

    def test_distro_overrides_recipe(self):
        with session.begin():
            lc = data_setup.create_labcontroller()
            system1 = data_setup.create_system(lab_controller=lc,
                arch=u'x86_64')
            i386_distro = self._create_i386_distro(lc)
            osmajor = i386_distro.osversion.osmajor
            io = OSMajorInstallOptions.lazy_create(osmajor_id=osmajor.id,
                arch_id=Arch.by_name('i386').id)
            io.ks_meta = 'lang=en_UK.UTF-8'
            session.expire(osmajor, ['install_options_by_arch'])
        recipe = self._create_recipe(system1)
        distro_tree_id = i386_distro.trees[0].id
        kickstart = self._run_create_kickstart(['--recipe-id', str(recipe.id),
            '--distro-tree-id', str(distro_tree_id),])

        # Make sure we are using the tree from --distro-tree-id
        self.assertIn('url=http://lab.test-kickstart.example.com/distros/'
            'RHEL-6.3/Workstation/i386/os/', kickstart)
        self.assertNotIn('url=http://lab.test-kickstart.invalid/distros/'
            'RHEL-6.2/Server/x86_64/os/', kickstart)
        self.assertIn('lang en_UK.UTF-8', kickstart)
        self.assertNotIn('lang en_US.UTF-8', kickstart)


    def test_distro_and_system_overrides_recipe(self):

        with session.begin():
            lc = data_setup.create_labcontroller()
            i386_distro = self._create_i386_distro(lc)
            system1 = data_setup.create_system(lab_controller=lc, arch=u'x86_64')
            system2 = data_setup.create_system(lab_controller=lc, arch=u'i386')
            system2.provisions[system2.arch[0]] = Provision(arch=system2.arch[0],
                kernel_options_post='usshopper')
        recipe = self._create_recipe(system1)

        # recipe uses system1 + x86_64 distro. We pass in system2 and i386
        # distro, so we should pick up the provision options of system2 + i386
        distro_tree_id = i386_distro.trees[0].id
        kickstart = self._run_create_kickstart(['--recipe-id', str(recipe.id),
                                                '--system', system2.fqdn,
                                                '--distro-tree-id', str(distro_tree_id),])

        # Make sure we are using the tree from --distro-tree-id
        self.assertIn('url=http://lab.test-kickstart.example.com/distros/'
            'RHEL-6.3/Workstation/i386/os/', kickstart)
        self.assertIn('usshopper', kickstart)
        # Make sure we are using system2
        self.assertIn(system2.fqdn, kickstart)
        self.assertNotIn(system1.fqdn, kickstart)
