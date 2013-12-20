import os
import sys
import tempfile
import shutil
import subprocess
import unittest2 as unittest
from cStringIO import StringIO
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.kickstart_helpers import create_rhel62, create_rhel62_server_x86_64, \
    create_lab_controller, create_x86_64_automated, compare_expected, \
    jinja_choice_loader, create_user
from bkr.server.tools import create_kickstart
from bkr.server.kickstart import template_env
from bkr.server.model import Task, User, Recipe

class CreateKickstartTest(unittest.TestCase):

    def setUp(self):
        self.orig_template_loader = template_env.loader
        template_env.loader = jinja_choice_loader(self.orig_template_loader)

    def tearDown(self):
        template_env.loader = self.orig_template_loader
        admin_user = User.by_user_name(data_setup.ADMIN_USER)
        if getattr(self,'recipe_id', None):
            with session.begin():
                recipe = Recipe.by_id(self.recipe_id)
                if recipe.resource.system.open_reservation:
                    recipe.resource.release()

    def _create_recipe(self):
        with session.begin():
            install_task = Task.by_name('/distribution/install')
            reserve_task = Task.by_name('/distribution/reservesys')
            lc = create_lab_controller()
            rhel62 = create_rhel62()
            rhel62_server_x86_64 = create_rhel62_server_x86_64(lab_controller=lc, distro=rhel62)
            system = create_x86_64_automated(lc)
            recipe = data_setup.create_recipe(distro_tree=rhel62_server_x86_64, task_list=[install_task, reserve_task])
            data_setup.create_job_for_recipes([recipe], owner=create_user(), whiteboard='')
            data_setup.mark_recipe_complete(recipe, system=system)
        self.recipe_id = recipe.id
        return recipe

    def _run_create_kickstart(self, args):
        # This is code for when we are in a dogfood task
        if 'BEAKER_LABCONTROLLER_HOSTNAME' in os.environ and \
            os.path.exists('/usr/bin/beaker-create-kickstart'):
            args.insert(0, '/usr/bin/beaker-create-kickstart')
            p = subprocess.Popen(args, stdout=subprocess.PIPE,
                stederr=subprocess.STDOUT)
            output, __ = p.communicate()
        else:
            # Running the test locally
            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            try:
                sys.stdout = my_out = StringIO()
                sys.stderr = None
                create_kickstart.main(args)
                output = my_out.getvalue()
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
        return output

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
                template_dir, '--recipe-id', recipe.id])
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
            '--recipe-id', recipe.id])
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
        generated_ks = self._run_create_kickstart(['--recipe-id', recipe.id])
        compare_expected('RedHatEnterpriseLinux6-scheduler-defaults', recipe.id,
               generated_ks)

    def test_rhel6_defaults_no_recipe(self):
        with session.begin():
            lc = create_lab_controller()
            system = create_x86_64_automated(lc)
            self.rhel62 = create_rhel62()
            self.rhel62_server_x86_64 = create_rhel62_server_x86_64(lab_controller=lc, distro=self.rhel62)
            user = create_user()
        session.expire_all()
        distro_tree_id = self.rhel62_server_x86_64.id
        generated_ks = self._run_create_kickstart(['--distro-tree-id',
            distro_tree_id, '--system', system.fqdn, '--user', user.user_name])
        compare_expected('RedHatEnterpriseLinux6-manual-defaults', None,
               generated_ks)
