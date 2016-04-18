from bkr.inttest.client import run_client, ClientTestCase
from bkr.inttest import data_setup, with_transaction
from bkr.server.model import Arch

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
