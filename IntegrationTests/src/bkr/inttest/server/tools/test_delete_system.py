
import unittest
from bkr.server.model import System, LabInfo, Provision, \
        ProvisionFamily, ProvisionFamilyUpdate
from turbogears.database import session
from bkr.inttest import data_setup, with_transaction
from bkr.server.tools.delete_system import delete_system

class DeleteSystemTest(unittest.TestCase):

    @with_transaction
    def setUp(self):
        self.system = data_setup.create_system()
        self.system.labinfo = LabInfo()
        self.system.labinfo.weight = 1
        distro = data_setup.create_distro()
        self.system.provisions[distro.arch] = \
                Provision(arch=distro.arch, ks_meta=u'lol1')
        self.system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor] = \
                ProvisionFamily(osmajor=distro.osversion.osmajor, ks_meta=u'lol2')
        self.system.provisions[distro.arch]\
            .provision_families[distro.osversion.osmajor]\
            .provision_family_updates[distro.osversion] = \
                ProvisionFamilyUpdate(osversion=distro.osversion, ks_meta=u'lol3')
        self.system_id = self.system.id

    def test_can_delete_system(self):
        delete_system(self.system.fqdn)
        self.assert_(System.query.get(self.system_id) is None)

    def test_dry_run_rolls_back(self):
        delete_system(self.system.fqdn, dry_run=True)
        self.assert_(System.query.get(self.system_id) is not None)

    def test_cannot_delete_system_which_has_been_used_for_recipes(self):
        with session.begin():
            job = data_setup.create_job()
            data_setup.mark_job_complete(job, system=self.system)

        try:
            delete_system(self.system.fqdn)
            self.fail('should raise')
        except ValueError:
            pass
        self.assert_(System.query.get(self.system_id) is not None)
