
import unittest
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.client import run_client

class WorkflowSimpleTest(unittest.TestCase):

    def setUp(self):
        self.distro = data_setup.create_distro(tags=[u'STABLE'])
        self.task = data_setup.create_task()
        data_setup.create_task(name=u'/distribution/install')
        data_setup.create_task(name=u'/distribution/reservesys')
        session.flush()

    def test_submit_job(self):
        out = run_client(['bkr', 'workflow-simple', '--random',
                '--arch', self.distro.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assert_(out.startswith('Submitted:'), out)

    def test_hostrequire(self):
        out = run_client(['bkr', 'workflow-simple',
                '--dryrun', '--prettyxml',
                '--hostrequire', 'hostlabcontroller=lab.example.com',
                '--arch', self.distro.arch.arch,
                '--family', self.distro.osversion.osmajor.osmajor,
                '--task', self.task.name])
        self.assert_('<hostlabcontroller op="=" value="lab.example.com"/>' in out, out)
