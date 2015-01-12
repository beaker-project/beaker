import pkg_resources
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import start_client, ClientTestCase


class WorkflowInstallerTest(ClientTestCase):

    def setUp(self):
        self.template_file_name = pkg_resources. \
            resource_filename('bkr.inttest.client', 'workflow_kickstart.cfg.tmpl')
        self.task = data_setup.create_task()

    def test_sanity(self):
        with session.begin():
            distro = data_setup.create_distro(tags=[u'STABLE'])
            distro_tree = data_setup.create_distro_tree(distro=distro)
        p = start_client(['bkr', 'workflow-installer-test',
            '--family', distro.osversion.osmajor.osmajor,
            '--arch', distro_tree.arch.arch,
            '--template', self.template_file_name,
            '--debug',
            '--task', self.task.name])
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertIn('key --skip', out)
        self.assertIn('Submitted:', out)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1078610
    def test_dryrun(self):
        with session.begin():
            distro = data_setup.create_distro(tags=[u'STABLE'])
            distro_tree = data_setup.create_distro_tree(distro=distro)
        p = start_client(['bkr', 'workflow-installer-test',
                          '--family', distro.osversion.osmajor.osmajor,
                          '--arch', distro_tree.arch.arch,
                          '--template', self.template_file_name,
                          '--task',
                          self.task.name,
                          '--dryrun'])
        out, err = p.communicate()
        self.assertEquals(p.returncode, 0)
        self.assertEquals('', out)
