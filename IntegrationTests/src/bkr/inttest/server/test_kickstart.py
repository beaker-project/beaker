
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import lxml.etree
import re
import unittest2 as unittest
import pipes
import crypt
from bkr.server import dynamic_virt
from bkr.server.model import session, DistroTreeRepo, LabControllerDistroTree, \
        CommandActivity, Provision, SSHPubKey, ProvisionFamily, OSMajor, Arch, \
        Key, Key_Value_String, OSMajorInstallOptions
from bkr.server.kickstart import template_env, generate_kickstart
from bkr.server.jobs import Jobs
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.inttest.kickstart_helpers import create_rhel62, create_rhel62_server_x86_64, \
    create_x86_64_automated, create_lab_controller, compare_expected, \
    jinja_choice_loader, create_user

# Not inheriting from DatabaseTestCase here because we have class-level setup,
# so we don't want to expunge it from the session after each case
class KickstartTest(unittest.TestCase):

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.orig_template_loader = template_env.loader
        template_env.loader = jinja_choice_loader(cls.orig_template_loader)
        with session.begin():
            cls.lab_controller = create_lab_controller()
            cls.system = create_x86_64_automated(cls.lab_controller)
            cls.system_s390x = data_setup.create_system(arch=u's390x',
                fqdn=u'test02.test-kickstart.invalid', status=u'Automated',
                lab_controller=cls.lab_controller)
            # set postreboot ksmeta for RHEL7
            s390x = Arch.by_name(u's390x')
            rhel7 = OSMajor.lazy_create(osmajor=u'RedHatEnterpriseLinux7')
            cls.system_s390x.provisions[s390x] = Provision(arch=s390x)
            cls.system_s390x.provisions[s390x].provision_families[rhel7] = \
                ProvisionFamily(osmajor=rhel7, ks_meta=u'postreboot')
            cls.system_armhfp = data_setup.create_system(arch=u'armhfp',
                fqdn=u'test03.test-kickstart.invalid', status=u'Automated',
                lab_controller=cls.lab_controller)

            cls.rhel39 = data_setup.create_distro(name=u'RHEL3-U9',
                osmajor=u'RedHatEnterpriseLinux3', osminor=u'9')
            cls.rhel39_as_x86_64 = data_setup.create_distro_tree(
                distro=cls.rhel39, variant=u'AS', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-3/U9/AS/x86_64/tree/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-3/U9/AS/x86_64/tree/'])
            cls.rhel39_as_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'repo-AS-x86_64', repo_type=u'os',
                    path=u'../repo-AS-x86_64'),
                DistroTreeRepo(repo_id=u'repo-debug-AS-x86_64', repo_type=u'debug',
                    path=u'../repo-debug-AS-x86_64'),
                DistroTreeRepo(repo_id=u'repo-srpm-AS-x86_64', repo_type=u'source',
                    path=u'../repo-srpm-AS-x86_64'),
            ]

            cls.rhel49 = data_setup.create_distro(name=u'RHEL4-U9',
                osmajor=u'RedHatEnterpriseLinux4', osminor=u'9')
            cls.rhel49_as_x86_64 = data_setup.create_distro_tree(
                distro=cls.rhel49, variant=u'AS', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-4/U9/AS/x86_64/tree/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-4/U9/AS/x86_64/tree/'])
            cls.rhel49_as_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'AS', repo_type=u'os',
                    path=u'../repo-AS-x86_64'),
            ]

            cls.rhel58server = data_setup.create_distro(name=u'RHEL5-Server-U8',
                osmajor=u'RedHatEnterpriseLinuxServer5', osminor=u'8')
            cls.rhel58server_x86_64 = data_setup.create_distro_tree(
                distro=cls.rhel58server, variant=u'', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-5-Server/U8/x86_64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-5-Server/U8/x86_64/os/'])
            cls.rhel58server_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'Cluster', repo_type=u'addon',
                    path=u'Cluster'),
                DistroTreeRepo(repo_id=u'ClusterStorage', repo_type=u'addon',
                    path=u'ClusterStorage'),
                DistroTreeRepo(repo_id=u'Server', repo_type=u'os',
                    path=u'Server'),
                DistroTreeRepo(repo_id=u'VT', repo_type=u'addon',
                    path=u'VT'),
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug',
                    path=u'../debug'),
            ]
            cls.rhel58server_ia64 = data_setup.create_distro_tree(
                distro=cls.rhel58server, variant=u'', arch=u'ia64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-5-Server/U8/ia64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-5-Server/U8/ia64/os/'])
            cls.rhel58server_ia64.repos[:] = [
                DistroTreeRepo(repo_id=u'Cluster', repo_type=u'addon',
                    path=u'Cluster'),
                DistroTreeRepo(repo_id=u'ClusterStorage', repo_type=u'addon',
                    path=u'ClusterStorage'),
                DistroTreeRepo(repo_id=u'Server', repo_type=u'os',
                    path=u'Server'),
                DistroTreeRepo(repo_id=u'VT', repo_type=u'addon',
                    path=u'VT'),
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug',
                    path=u'../debug'),
            ]

            cls.rhel62 = create_rhel62()
            cls.rhel62_server_x86_64 = create_rhel62_server_x86_64(cls.rhel62, cls.lab_controller)
            cls.rhel62_server_ppc64 = data_setup.create_distro_tree(
                distro=cls.rhel62, variant=u'Server', arch=u'ppc64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/ppc64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-6.2/Server/ppc64/os/'])
            cls.rhel62_server_ppc64.repos[:] = [
                DistroTreeRepo(repo_id=u'Server', repo_type=u'os', path=u'Server'),
                DistroTreeRepo(repo_id=u'optional-ppc64-os', repo_type=u'addon',
                    path=u'../../optional/ppc64/os'),
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug',
                    path=u'../debug'),
                DistroTreeRepo(repo_id=u'optional-ppc64-debug', repo_type=u'debug',
                    path=u'../../optional/ppc64/debug'),
            ]
            cls.rhel62_server_s390x = data_setup.create_distro_tree(
                distro=cls.rhel62, variant=u'Server', arch=u's390x',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/s390x/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-6.2/Server/s390x/os/'])
            cls.rhel62_server_s390x.repos[:] = [
                DistroTreeRepo(repo_id=u'Server', repo_type=u'os', path=u'Server'),
                DistroTreeRepo(repo_id=u'optional-s390x-os', repo_type=u'addon',
                    path=u'../../optional/s390x/os'),
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug',
                    path=u'../debug'),
                DistroTreeRepo(repo_id=u'optional-s390x-debug', repo_type=u'debug',
                    path=u'../../optional/s390x/debug'),
            ]

            cls.rhel70nightly = data_setup.create_distro(name=u'RHEL-7.0-20120314.0',
                osmajor=u'RedHatEnterpriseLinux7', osminor=u'0')
            cls.rhel70nightly_workstation_x86_64 = data_setup.create_distro_tree(
                distro=cls.rhel70nightly, variant=u'Workstation', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/os/',
                      u'nfs+iso://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/iso/'])
            cls.rhel70nightly_workstation_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'repos_debug_Workstation_optional',
                    repo_type=u'debug',
                    path=u'../../../Workstation-optional/x86_64/debuginfo'),
                DistroTreeRepo(repo_id=u'repos_debug_Workstation', repo_type=u'debug',
                    path=u'../debuginfo'),
                DistroTreeRepo(repo_id=u'repos_Workstation-optional', repo_type=u'addon',
                    path=u'../../../Workstation-optional/x86_64/os'),
                DistroTreeRepo(repo_id=u'repos_Workstation', repo_type=u'os', path=u'.'),
                DistroTreeRepo(repo_id=u'repos_addons_ScalableFileSystem',
                    repo_type=u'addon', path=u'addons/ScalableFileSystem'),
            ]
            cls.rhel70nightly_server_s390x = data_setup.create_distro_tree(
                distro=cls.rhel70nightly, variant=u'Server', arch=u's390x',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Server/s390x/os/'])
            cls.rhel70nightly_server_s390x.repos[:] = [
                DistroTreeRepo(repo_id=u'repos_debug_Server_optional',
                    repo_type=u'debug',
                    path=u'../../../Server-optional/s390x/debuginfo'),
                DistroTreeRepo(repo_id=u'repos_debug_Server', repo_type=u'debug',
                    path=u'../debuginfo'),
                DistroTreeRepo(repo_id=u'repos_Server-optional', repo_type=u'addon',
                    path=u'../../../Server-optional/s390x/os'),
                DistroTreeRepo(repo_id=u'repos_Server', repo_type=u'os', path=u'.'),
            ]
            cls.rhel70nightly_server_ppc64 = data_setup.create_distro_tree(
                distro=cls.rhel70nightly, variant=u'Server', arch=u'ppc64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Server/ppc64/os/'])
            cls.rhel70nightly_server_ppc64.repos[:] = [
                DistroTreeRepo(repo_id=u'repos_debug_Server_optional',
                    repo_type=u'debug',
                    path=u'../../../Server-optional/ppc64/debuginfo'),
                DistroTreeRepo(repo_id=u'repos_debug_Server', repo_type=u'debug',
                    path=u'../debuginfo'),
                DistroTreeRepo(repo_id=u'repos_Server-optional', repo_type=u'addon',
                    path=u'../../../Server-optional/ppc64/os'),
                DistroTreeRepo(repo_id=u'repos_Server', repo_type=u'os', path=u'.'),
            ]

            cls.centos7 = data_setup.create_distro(name=u'CentOS-7',
                osmajor=u'CentOS7', osminor=u'0')
            cls.centos7_x86_64 = data_setup.create_distro_tree(
                distro=cls.centos7, variant=u'', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/CentOS-7/os/x86_64/'])
            cls.centos7_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'distro', repo_type=u'distro', path=u'.'),
            ]

            cls.f17 = data_setup.create_distro(name=u'Fedora-17',
                osmajor=u'Fedora17', osminor=u'0')
            cls.f17_armhfp = data_setup.create_distro_tree(
                distro=cls.f17, variant=u'Fedora', arch=u'armhfp',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/F-17/GOLD/Fedora/armhfp/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/F-17/GOLD/Fedora/armhfp/os/'])
            cls.f17_armhfp.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]

            cls.f18 = data_setup.create_distro(name=u'Fedora-18',
                osmajor=u'Fedora18', osminor=u'0')
            cls.f18_x86_64 = data_setup.create_distro_tree(
                distro=cls.f18, variant=u'Fedora', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/F-18/GOLD/Fedora/x86_64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/F-18/GOLD/Fedora/x86_64/os/'])
            cls.f18_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]
            cls.f18_armhfp = data_setup.create_distro_tree(
                distro=cls.f18, variant=u'Fedora', arch=u'armhfp',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/F-18/GOLD/Fedora/armhfp/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/F-18/GOLD/Fedora/armhfp/os/'])
            cls.f18_armhfp.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]

            cls.frawhide = data_setup.create_distro(name=u'Fedora-rawhide',
                osmajor=u'Fedorarawhide', osminor=u'0')
            cls.frawhide_x86_64 = data_setup.create_distro_tree(
                distro=cls.frawhide, variant=u'Fedora', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/development/rawhide/x86_64/os/',
                      u'nfs://lab.test-kickstart.invalid/distros/development/rawhide/x86_64/os/'])
            cls.frawhide_x86_64.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]
            cls.frawhide_ppc = data_setup.create_distro_tree(
                distro=cls.frawhide, variant=u'Fedora', arch=u'ppc',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/development/rawhide/ppc/os/',
                      u'nfs://lab.test-kickstart.invalid/distros/development/rawhide/ppc/os/'])
            cls.frawhide_ppc.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]
            cls.frawhide_ppc64 = data_setup.create_distro_tree(
                distro=cls.frawhide, variant=u'Fedora', arch=u'ppc64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/development/rawhide/ppc64/os/',
                      u'nfs://lab.test-kickstart.invalid/distros/development/rawhide/ppc64/os/'])
            cls.frawhide_ppc64.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]
            cls.frawhide_ppc64le = data_setup.create_distro_tree(
                distro=cls.frawhide, variant=u'Fedora', arch=u'ppc64le',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/development/rawhide/ppc64le/os/',
                      u'nfs://lab.test-kickstart.invalid/distros/development/rawhide/ppc64le/os/'])
            cls.frawhide_ppc64le.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]

            cls.frawhide_aarch64 = data_setup.create_distro_tree(
                distro=cls.frawhide, variant=u'Fedora', arch=u'aarch64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/development/rawhide/aarch64/os/',
                      u'nfs://lab.test-kickstart.invalid/distros/development/rawhide/aarch64/os/'])
            cls.frawhide_aarch64.repos[:] = [
                DistroTreeRepo(repo_id=u'debug', repo_type=u'debug', path=u'../debug'),
            ]

            cls.atomic = data_setup.create_distro(name=u'Atomic-Host',
                osmajor=u'AtomicHost', osminor=u'0')
            cls.atomic_x86_64 = data_setup.create_distro_tree(
                distro=cls.atomic, variant=u'', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/atomic/images/PXE/'])

            atomic_osmajor = cls.atomic_x86_64.distro.osversion.osmajor
            OSMajorInstallOptions(osmajor=atomic_osmajor, arch=cls.atomic_x86_64.arch,
                ks_meta=u'has_rpmostree bootloader_type=extlinux')

        # This forces any subsequent access of the above ORM objects to retrieve
        # the data from the DB, thus ensuring that relationships are ordered correctly.
        # Correct ordering of relationships are needed to ensure that the kickstarts
        # are rendered as expected.
        session.expire_all()

    def setUp(self):
        session.begin()
        self.user = create_user()

    def tearDown(self):
        session.rollback()

    @classmethod
    def tearDownClass(cls):
        session.close()
        template_env.loader = cls.orig_template_loader

    def provision_recipe(self, xml, system=None, virt=False):
        """
        Pass either system, or virt=True.
        """
        xmljob = lxml.etree.fromstring(xml)
        job = Jobs().process_xmljob(xmljob, self.user)
        recipe = job.recipesets[0].recipes[0]
        session.flush()
        data_setup.mark_job_complete(job, system=system,
                virt=virt, lab_controller=self.lab_controller)
        return recipe

    def test_rhel3_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL3-U9" />
                            <distro_variant op="=" value="AS" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('RedHatEnterpriseLinux3-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel3_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--enableshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL3-U9" />
                            <distro_variant op="=" value="AS" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nauthconfig --enableshadow --enablemd5\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_rhel4_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL4-U9" />
                            <distro_variant op="=" value="AS" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('RedHatEnterpriseLinux4-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel4_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--enableshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL4-U9" />
                            <distro_variant op="=" value="AS" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nauthconfig --enableshadow --enablemd5\n',
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel5server_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('RedHatEnterpriseLinuxServer5-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel5server_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--useshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assertIn('\nauth --useshadow --enablemd5\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_rhel5server_repos(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <repos>
                            <repo name="custom"
                            url="http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinuxServer5/"/>
                        </repos>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assert_(r'''repo --name=custom --baseurl=http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinuxServer5/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

        for line in recipe.installation.rendered_kickstart.kickstart.splitlines():
            if line.startswith('repo'):
                self.assert_(r'''--cost'''
                             not in line, 
                             line)

    def test_rhel6_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('RedHatEnterpriseLinux6-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--useshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nauth --useshadow --enablemd5\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_http(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="method=http">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assert_(r'''url --url=http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/x86_64/os/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_ondisk(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="ondisk=/dev/sda">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        ondisk_lines = [r'''clearpart --drives /dev/sda --all --initlabel''',
                       r'''part /boot --size 250 --recommended --asprimary --ondisk=/dev/sda''',
                       r'''part / --size 1024 --grow --ondisk=/dev/sda''',
                       r'''part swap --recommended --ondisk=/dev/sda''']

        for line in ondisk_lines:
            self.assert_(line in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                         recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_partitions(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="home" size="5" />
                        </partitions>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        part_lines = [r'''part /boot --size 250 --recommended --asprimary''',
                      r'''part / --size 1024 --grow''',
                      r'''part swap --recommended''',
                      r'''part /home --size=5120 --fstype ext4''']

        for line in part_lines:
            self.assert_(line in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                         recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_repos(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <repos>
                            <repo name="custom"
                            url="http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinux6/"/>
                        </repos>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assert_(r'''repo --name=custom --cost=100 --baseurl=http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinux6/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)


    def test_rhel6_s390x(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="s390x" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system_s390x)

        self.assert_(r'''nfs --server lab.test-kickstart.invalid --dir /distros/RHEL-6.2/Server/s390x/os/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

        self.assert_(r'''xconfig''' not in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

        self.assert_(r'''vmcp ipl''' in recipe.installation.rendered_kickstart.kickstart,
                     recipe.installation.rendered_kickstart.kickstart)


    def test_rhel6_unsupported_hardware(self):

        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'unsupported_hardware')

        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)

        self.assert_(r'''unsupported_hardware''' in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_guest_console(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestargs="--ram=1024 vcpus=1">
                            <distroRequires>
                                <distro_name op="=" value="RHEL-6.2" />
                                <distro_arch op="=" value="x86_64" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" />
                            <task name="/distribution/reservesys" />
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>''', self.system)
        guest = recipe.guests[0]
        ks = guest.installation.rendered_kickstart.kickstart
        compare_expected('RedHatEnterpriseLinux6-scheduler-guest', guest.id,
                         ks)

    def test_rhel6_autopart_type_ignored(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="autopart_type='xfs'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertNotIn('\nautopart --type xfs\n',
                         recipe.installation.rendered_kickstart.kickstart)
        self.assertIn('\nautopart\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('RedHatEnterpriseLinux7-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_nfs_iso(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="method=nfs+iso">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assert_(r'''nfs --server lab.test-kickstart.invalid --dir /distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/iso/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--useshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nauth --useshadow --enablemd5\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_manual(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                                          fqdn='test-manual-1.test-kickstart.invalid',
                                          lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'manual')

        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)

        compare_expected('RedHatEnterpriseLinux7-scheduler-manual', recipe.id,
                         recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_repos(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <repos>
                            <repo name="custom"
                            url="http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinux7/"/>
                        </repos>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assert_(r'''repo --name=custom --cost=100 --baseurl=http://repos.fedorapeople.org/repos/beaker/server/RedHatEnterpriseLinux7/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_s390x(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="s390x" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system_s390x)

        self.assert_(r'''url --url=http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Server/s390x/os/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

        self.assert_(r'''xconfig''' not in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

        self.assert_(r'''vmcp ipl''' not in recipe.installation.rendered_kickstart.kickstart,
                     recipe.installation.rendered_kickstart.kickstart)

    def test_rhel7_autopart_type(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="autopart_type='xfs'">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nautopart --type xfs\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_fedora18_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('Fedora18-scheduler-defaults', recipe.id,
                recipe.installation.rendered_kickstart.kickstart)

    def test_fedora18_auth(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="auth='--useshadow --enablemd5'">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nauth --useshadow --enablemd5\n',
                     recipe.installation.rendered_kickstart.kickstart)

    def test_fedora_repos(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <repos>
                            <repo name="custom"
                            url="http://repos.fedorapeople.org/repos/beaker/server/Fedora18/"/>
                        </repos>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assert_(r'''repo --name=custom --cost=100 --baseurl=http://repos.fedorapeople.org/repos/beaker/server/Fedora18/'''
                     in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                     recipe.installation.rendered_kickstart.kickstart)

    def test_fedora_rawhide_defaults(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('Fedorarawhide-scheduler-defaults', recipe.id,
                         recipe.installation.rendered_kickstart.kickstart)

    def test_fedora_rawhide_autopart_type(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="autopart_type='xfs'">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertIn('\nautopart --type xfs\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_job_group_clear_text_password(self):
        # set clear text password
        root_password = 'blappy7'
        group = data_setup.create_group(group_name='group1',
                                        root_password=root_password)
        group.add_member(self.user)
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        session.commit()
        session.begin()

        recipe = self.provision_recipe('''
            <job group='group1'>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)

        for line in recipe.installation.rendered_kickstart.kickstart.splitlines():
            if line.startswith('rootpw'):
                crypted_root_password = line.split()[2]
                self.assertEquals(crypt.crypt(root_password, crypted_root_password),
                                  crypted_root_password)
                break

    def test_group_job_crypted_password(self):
        # set crypted password
        crypted_root_password = crypt.crypt('blappy7', "$1$%s$")
        group = data_setup.create_group(group_name='group1',
                                        root_password=crypted_root_password)
        group.add_member(self.user)
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        session.commit()
        session.begin()

        recipe = self.provision_recipe('''
            <job group='group1'>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)

        self.assert_(
            'rootpw --iscrypted %s' % crypted_root_password
            in recipe.installation.rendered_kickstart.kickstart.splitlines(),
            recipe.installation.rendered_kickstart.kickstart)

    def test_ignoredisk(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'ignoredisk=--only-use=sda')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_(
                r'''ignoredisk --only-use=sda'''
                in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

    def test_skipx(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'skipx')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_(
                r'''skipx'''
                in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_manual(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                                          fqdn='test-manual-1.test-kickstart.invalid',
                                          lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'manual')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)

        compare_expected('RedHatEnterpriseLinux6-scheduler-manual', recipe.id,
                         recipe.installation.rendered_kickstart.kickstart)

    def test_leavebootorder(self):
        system = data_setup.create_system(arch=[u'ppc64', u'ppc64le'], status=u'Automated',
                lab_controller=self.lab_controller)
        # ppc64
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0])
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="ppc64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_(
                r'''bootloader --location=mbr --leavebootorder'''
                in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

        # ppc64le
        system.provisions[system.arch[1]] = Provision(arch=system.arch[1])
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="ppc64le" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_(
                r'''bootloader --location=mbr --leavebootorder'''
                in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

        # --leavebootorder is only in RHEL7+ and F18+
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="ppc64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assertNotIn('--leavebootorder', recipe.installation.rendered_kickstart.kickstart)

    def test_grubport(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'grubport=0x02f8')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assertIn('--port=0x02f8', recipe.installation.rendered_kickstart.kickstart)

    def test_rhel5_devices(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'scsidevices=cciss')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_('device scsi cciss' in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

    def test_rhel6_devices(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                ks_meta=u'scsidevices=cciss')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_('device cciss' in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

    def test_kopts_post(self):
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        system.provisions[system.arch[0]] = Provision(arch=system.arch[0],
                kernel_options_post=u'console=ttyS0,9600n8 pci=nomsi')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_('bootloader --location=mbr --append="console=ttyS0,9600n8 pci=nomsi"'
                in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                recipe.installation.rendered_kickstart.kickstart)

    def test_partitions_lvm(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition type="lvm" fs="btrfs" name="butter" size="25" />
                        </partitions>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assert_('''
part /boot --size 250 --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
part pv.001 --size=25605
volgroup TestVolume001 pv.001
logvol /butter --name=butter --vgname=TestVolume001 --size=25600 --fstype btrfs
'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    def test_sshkeys_group(self):
        self.user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'neveroddoreven', u'description'))
        user2 = data_setup.create_user()
        user2.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'murderforajarofredrum', u'description'))
        group = data_setup.create_group(group_name=data_setup.unique_name('group%s'))
        group.add_member(self.user)
        group.add_member(user2)
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        recipe = self.provision_recipe('''
            <job group="%s">
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''' % group.group_name, system)

        self.assert_('''
mkdir -p /root/.ssh
cat >>/root/.ssh/authorized_keys <<"__EOF__"
ssh-rsa neveroddoreven description
ssh-rsa murderforajarofredrum description
__EOF__
restorecon -R /root/.ssh
chmod go-w /root /root/.ssh /root/.ssh/authorized_keys
'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    def test_sshkeys(self):
        self.user.root_password = '$1$beaker$yMeLK4p1IVkFa80RyTkpE.'
        self.user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'lolthisismykey', u'description'))
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        self.assert_('''
mkdir -p /root/.ssh
cat >>/root/.ssh/authorized_keys <<"__EOF__"
ssh-rsa lolthisismykey description
__EOF__
restorecon -R /root/.ssh
chmod go-w /root /root/.ssh /root/.ssh/authorized_keys
'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=832226
    def test_sshkeys_s390x(self):
        self.user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'AAAAhhh', u'help'))
        system = data_setup.create_system(arch=u's390x', status=u'Automated',
                lab_controller=self.lab_controller)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_family op="=" value="RedHatEnterpriseLinux7" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="s390x" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        # check the reboot snippet is after the ssh key
        self.assert_('Force a reboot'
                     in recipe.installation.rendered_kickstart.kickstart.split('cat >>/root/.ssh/authorized_keys')[1],
                     recipe.installation.rendered_kickstart.kickstart)

    def test_ksappends(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <ks_appends>
                            <ks_append>
%post
echo Hello World
%end</ks_append>
                        </ks_appends>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assert_('''
%post
echo Hello World
%end'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    def test_custom_kickstart_rhel6(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr

%packages 
mysillypackage
%end
                        ]]></kickstart>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_(k.startswith('nfs --server lab.test-kickstart.invalid '
                                  '--dir /distros/RHEL-6.2/Server/x86_64/os/'), k)
        self.assert_('''
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr
'''
                in k, k)

        self.assertNotIn('''
cat >> /etc/profile.d/task-overrides-rhts.sh <<END
export RHTS_OPTION_COMPATIBLE=
export RHTS_OPTION_COMPAT_SERVICE=
END
%end''', k)

        klines = k.splitlines()
        self.assert_('mysillypackage' in klines, k)
        # should also contain the various Beaker bits
        self.assert_('%pre --log=/dev/console' in klines, k)
        self.assert_('# Check in with Beaker Server' in klines, k)
        self.assert_('%post --log=/dev/console' in klines, k)
        self.assert_('# Add Harness Repo' in klines, k)
        self.assert_('yum -y install beah rhts-test-env beakerlib' in klines, k)

    def test_custom_kickstart_rhel7(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr

%packages 
mysillypackage
%end
                        ]]></kickstart>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_(k.startswith('url --url=http://lab.test-kickstart.invalid'
                '/distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/os/\n'), k)
        self.assert_('''
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr
'''
                in k, k)

        self.assertIn('''
cat >> /etc/profile.d/task-overrides-rhts.sh <<END
export RHTS_OPTION_COMPATIBLE=
export RHTS_OPTION_COMPAT_SERVICE=
END
%end''', k)

        klines = k.splitlines()
        self.assert_('mysillypackage' in klines, k)
        # should also contain the various Beaker bits
        self.assert_('%pre --log=/dev/console' in klines, k)
        self.assert_('# Check in with Beaker Server' in klines, k)
        self.assert_('%post --log=/dev/console' in klines, k)
        self.assert_('# Add Harness Repo' in klines, k)
        self.assert_('yum -y install beah rhts-test-env beakerlib' in klines, k)

    def test_custom_kickstart_fedora_rawhide(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr

%packages 
mysillypackage
%end
                        ]]></kickstart>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_(k.startswith('nfs --server lab.test-kickstart.invalid '
                                  '--dir /distros/development/rawhide/x86_64/os/'), k)
        self.assert_('''
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr
'''
                in k, k)

        self.assertIn('''
cat >> /etc/profile.d/task-overrides-rhts.sh <<END
export RHTS_OPTION_COMPATIBLE=
export RHTS_OPTION_COMPAT_SERVICE=
END
%end''', k)

        klines = k.splitlines()
        self.assert_('mysillypackage' in klines, k)
        # should also contain the various Beaker bits
        self.assert_('%pre --log=/dev/console' in klines, k)
        self.assert_('# Check in with Beaker Server' in klines, k)
        self.assert_('%post --log=/dev/console' in klines, k)
        self.assert_('# Add Harness Repo' in klines, k)
        self.assert_('yum -y install beah rhts-test-env beakerlib' in klines, k)

    def test_custom_kickstart_fedora(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr

%packages 
mysillypackage
%end
                        ]]></kickstart>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_(k.startswith('nfs --server lab.test-kickstart.invalid ' 
                                  '--dir /distros/F-18/GOLD/Fedora/x86_64/os/'), k)
        self.assert_('''
install
lang en_AU.UTF-8
timezone --utc Australia/Brisbane
rootpw --iscrypted $1$beaker$yMeLK4p1IVkFa80RyTkpE.
selinux --enforcing
firewall --service=ssh
bootloader --location=mbr
'''
                in k, k)

        self.assertIn('''
cat >> /etc/profile.d/task-overrides-rhts.sh <<END
export RHTS_OPTION_COMPATIBLE=
export RHTS_OPTION_COMPAT_SERVICE=
END
%end''', k)

        klines = k.splitlines()
        self.assert_('mysillypackage' in klines, k)
        # should also contain the various Beaker bits
        self.assert_('%pre --log=/dev/console' in klines, k)
        self.assert_('# Check in with Beaker Server' in klines, k)
        self.assert_('%post --log=/dev/console' in klines, k)
        self.assert_('# Add Harness Repo' in klines, k)
        self.assert_('yum -y install beah rhts-test-env beakerlib' in klines, k)


    # https://bugzilla.redhat.com/show_bug.cgi?id=801676
    def test_custom_kickstart_ssh_keys(self):
        self.user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'lolthisismykey', u'description'))
        system = data_setup.create_system(arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
%packages
mysillypackage
%end
                        ]]></kickstart>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('ssh-rsa lolthisismykey description' in k.splitlines(), k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1077251
    def test_custom_kickstart_can_access_model_objects(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
{% if distro_tree is arch('i386', 'x86_64') %}
# arch test is true
{% endif %}
{% if distro is osversion('RedHatEnterpriseLinux7.0', 'CentOS7.0') %}
# osversion test is true
{% endif %}
{% if distro is osmajor('RedHatEnterpriseLinux7', 'CentOS7') %}
# osmajor test is true
{% endif %}
{% if distro.osversion.osmajor.name == 'RedHatEnterpriseLinux' and distro.osversion.osmajor.number|int >= 6 %}
# conditional using osmajor name and number is true
{% endif %}
{% if distro_tree.variant == 'Workstation' %}
# variant test is true
{% endif %}
# tree url is {{ distro_tree.url_in_lab(lab_controller, required=True) }}
# recipe id is {{ recipe.id }}
                        ]]></kickstart>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
install
# arch test is true
# osversion test is true
# osmajor test is true
# conditional using osmajor name and number is true
# variant test is true
# tree url is http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/os/
''', ks)
        self.assertIn('\n# recipe id is %s\n' % recipe.id, ks)

    def test_custom_kickstart_rhel5_with_conflicts_groups(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
%packages
*
{% for group in conflicts_groups %}
-@{{ group }}
{% endfor %}
%end
                        ]]></kickstart>
                        <task name="/distribution/utils/dummy" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
install
%packages
*
-@conflicts
%end
''', ks)

    def test_custom_kickstart_rhel7_with_conflicts_groups(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
%packages
*
{% for group in conflicts_groups %}
-@{{ group }}
{% endfor %}
%end
                        ]]></kickstart>
                        <task name="/distribution/utils/dummy" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
install
%packages
*
-@conflicts-workstation
%end
''', ks)

    def test_custom_kickstart_centos7_with_conflicts_groups(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="CentOS-7" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
%packages
*
{% for group in conflicts_groups %}
-@{{ group }}
{% endfor %}
%end
                        ]]></kickstart>
                        <task name="/distribution/utils/dummy" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
install
%packages
*
-@conflicts-client
-@conflicts-server
-@conflicts-workstation
%end
''', ks)

    def test_custom_kickstart_fedora_without_conflicts_groups(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <kickstart><![CDATA[
install
%packages
*
{% for group in conflicts_groups %}
-{{ group }}
{% endfor %}
%end
                        ]]></kickstart>
                        <task name="/distribution/utils/dummy" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
install
%packages
*
%end
''', ks)

    def test_no_debug_repos(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="no_debug_repos">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('repo --name=beaker-debug' not in k, k)
        self.assert_('repo --name=beaker-optional-x86_64-debug' not in k, k)
        self.assert_('/etc/yum.repos.d/beaker-debug.repo' not in k, k)
        self.assert_('/etc/yum.repos.d/beaker-optional-x86_64-debug.repo' not in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=874191
    def test_no_updates_repos_fedora(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="no_updates_repos">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('repo --name=fedora-updates' not in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1202075
    def test_disable_repos_configured_by_fedora_release(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="no_updates_repos">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('''
sed -i -e '/\[fedora\]/,/^\[/s/enabled=1/enabled=0/' /etc/yum.repos.d/fedora.repo
'''
    in k, k)
        self.assert_('''
sed -i -e '/\[updates\]/,/^\[/s/enabled=1/enabled=0/' /etc/yum.repos.d/fedora-updates.repo
'''
    in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=869758
    def test_repo_url_containing_yum_variable(self):
        # Anaconda can't substitute yum variables like $releasever, so to avoid
        # breakages we don't pass it any repo URLs containing $
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <repos>
                            <repo name="custom" url="http://example.com/$releasever/"/>
                        </repos>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('repo --name=custom' not in k, k)
        self.assert_('# skipping custom' in k, k)

    def test_beaker_url(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('export BEAKER="%s"' % get_server_base() in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691442
    def test_whiteboards(self):
        # This test checks that the job and recipe whiteboards are made
        # available in the test environments via the kickstart templates
        whiteboard = '''This "1"\nIs '2'a'''
        recipe_xml = '''
            <job>
                <whiteboard>Job: %s</whiteboard>
                <recipeSet>
                    <recipe whiteboard="Recipe: %s">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''' % (whiteboard, whiteboard.replace('"', "&quot;"))
        recipe_entry = ("Recipe: " +
                        " ".join(line for line in whiteboard.splitlines()))
        recipe = self.provision_recipe(recipe_xml, self.system)
        recipe_whiteboard = recipe.whiteboard
        self.assertEqual(recipe_whiteboard, recipe_entry)

        job_entry = "Job: " + whiteboard
        job_whiteboard = recipe.recipeset.job.whiteboard
        self.assertEqual(job_whiteboard, job_entry)

        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn("""export BEAKER_JOB_WHITEBOARD='Job: This "1"\nIs '"'"'2'"'"'a'""", ks)
        self.assertIn("""export BEAKER_RECIPE_WHITEBOARD='Recipe: This "1" Is '"'"'2'"'"'a'""", ks)
        self.assertIn("""setenv BEAKER_JOB_WHITEBOARD 'Job: This "1"\nIs '"'"'2'"'"'a'""", ks)
        self.assertIn("""setenv BEAKER_RECIPE_WHITEBOARD 'Recipe: This "1" Is '"'"'2'"'"'a'""", ks)

    def test_no_whiteboards(self):
        # This test checks that everything works as expected with no
        # recipe whiteboard defined and an empty job whiteboard
        recipe_xml = '''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        recipe = self.provision_recipe(recipe_xml, self.system)
        self.assertEqual(recipe.whiteboard, None)
        self.assertEqual(recipe.recipeset.job.whiteboard, "")
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assert_("export BEAKER_JOB_WHITEBOARD=''" in ks, ks)
        self.assert_("export BEAKER_RECIPE_WHITEBOARD=''" in ks, ks)
        self.assert_("setenv BEAKER_JOB_WHITEBOARD ''" in ks, ks)
        self.assert_("setenv BEAKER_RECIPE_WHITEBOARD ''" in ks, ks)

    def test_no_recipe(self):
        # This test checks that everything works as expected with no
        # recipe defined at all (which can happen when systems are
        # switched to manual mode instead of automatic)
        tree = self.rhel62_server_x86_64
        ks = generate_kickstart(self.system.manual_provision_install_options(tree),
                                tree, self.system, self.user).kickstart
        compare_expected('RedHatEnterpriseLinux6-manual-defaults', None, ks)

    def test_no_system_or_recipe(self):
        # We need one or the other in order to find the lab controller
        tree = self.rhel62_server_x86_64
        self.assertRaises(ValueError, generate_kickstart,
                          self.system.manual_provision_install_options(tree),
                          tree, None, None)

    # https://bugzilla.redhat.com/show_bug.cgi?id=834147
    def test_ftp_no_http(self):
        ftp_lc = data_setup.create_labcontroller()
        system = data_setup.create_system(arch=u'x86_64', lab_controller=ftp_lc)
        self.rhel62_server_x86_64.lab_controller_assocs.append(
                LabControllerDistroTree(lab_controller=ftp_lc, url=u'ftp://something/'))
        session.flush()
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('repo --name=beaker-Server --cost=100 --baseurl=ftp://something/Server' in k, k)
        self.assert_('name=beaker-Server\nbaseurl=ftp://something/Server' in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=838671
    def test_root_password(self):
        self.user.root_password = None
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        for line in recipe.installation.rendered_kickstart.kickstart.split('\n'):
            match = re.match("rootpw --iscrypted (.*)", line)
            if match:
                self.assert_(crypt.crypt('beaker', match.group(1)) == match.group(1))
                break
        else:
           self.fail("Password missing from kickstart")

    # https://bugzilla.redhat.com/show_bug.cgi?id=743441
    def test_rootfstype(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="rootfstype=btrfs">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assert_('''
part /boot --size 250 --recommended --asprimary
part / --size 1024 --grow --fstype btrfs
part swap --recommended

'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=865679
    def test_fstype(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=ext4">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assert_('''
part /boot --size 250 --recommended --asprimary --fstype ext4
part / --size 1024 --grow --fstype ext4
part swap --recommended

'''
                in recipe.installation.rendered_kickstart.kickstart,
                recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=578812
    def test_static_networks(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="static_networks=00:11:22:33:44:55,192.168.99.1/24;66:77:88:99:aa:bb,192.168.100.1/24">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('''
network --bootproto=dhcp
network --bootproto=static --device=00:11:22:33:44:55 --ip=192.168.99.1 --netmask=255.255.255.0
network --bootproto=static --device=66:77:88:99:aa:bb --ip=192.168.100.1 --netmask=255.255.255.0
''' in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=920470
    def test_dhcp_networks(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="dhcp_networks=00:11:22:33:44:55;66:77:88:99:aa:bb">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('''
network --bootproto=dhcp
network --bootproto=dhcp --device=00:11:22:33:44:55
network --bootproto=dhcp --device=66:77:88:99:aa:bb
''' in k, k)

    def test_highbank(self):
        system = data_setup.create_system(arch=u'armhfp', status=u'Automated',
                lab_controller=self.lab_controller, kernel_type=u'highbank')
        session.flush()
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="armhfp" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('# Install U-Boot boot.scr' in k.splitlines(), k)
        self.assert_('Highbank Fedora' in k, k)

    def test_mvebu(self):
        system = data_setup.create_system(arch=u'armhfp', status=u'Automated',
                lab_controller=self.lab_controller, kernel_type=u'mvebu')
        session.flush()
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="armhfp" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('# Install U-Boot boot.scr' in k.splitlines(), k)
        self.assert_('Yosemite Fedora' in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=728410
    def test_per_system_packages(self):
        system = data_setup.create_system(fqdn=u'bz728410-system-with-packages',
                arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        session.flush()
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('special-weird-driver-package' in k.splitlines(), k)

    def test_packages_arent_duplicated(self):
        system = data_setup.create_system(fqdn=u'testForPackageDuplication',
                arch=u'x86_64', status=u'Automated',
                lab_controller=self.lab_controller)
        task1 = data_setup.create_task(requires=[u'requires1'])
        task2 = data_setup.create_task(requires=[u'requires1'])
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="%s" />
                        <task name="%s" />
                    </recipe>
                </recipeSet>
            </job>
            ''' % (task1.name, task2.name), system)
        k = recipe.installation.rendered_kickstart.kickstart
        kickstart_lines = k.splitlines()
        self.assert_(kickstart_lines.count('requires1') == 1)

    def test_packages_ksmeta_replaces_recipe_packages(self):
        # Users can pass a colon-separated list of packages in ksmeta and it 
        # will replace all the recipe packages (from <packages/> and task 
        # requirements).
        # This was never really intended behaviour (since it's not very 
        # useful), it was just a side-effect of how Beaker passed recipe 
        # packages to Cobbler through ksmeta. However to avoid breaking 
        # compatibility we need to continue supporting it.
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="packages=@core:httpd">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        k = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('''\
%packages --ignoremissing
@core
httpd
# no snippet data for packages
%end
''', k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=952635
    def test_task_requirements_with_colons_are_preserved(self):
        # Note that no package ever contains colons in its name, and a task 
        # cannot use arbitrary RPM virtual requirements (like 
        # perl(Archive::Tar) or similar), it has to depend on actual package 
        # names because Anaconda only accepts real package names in %packages. 
        # But, for completelness, we ensure colons are preserved as is in the 
        # kickstart.
        task = data_setup.create_task(requires=[u'some::weird::package'])
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="%s" />
                    </recipe>
                </recipeSet>
            </job>
            ''' % task.name)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('%packages --ignoremissing\nsome::weird::package\n', k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=865680
    def test_linkdelay(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="linkdelay=20">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('''
for cfg in /etc/sysconfig/network-scripts/ifcfg-* ; do
    if [ "$(basename "$cfg")" != "ifcfg-lo" ] ; then
        echo "LINKDELAY=20" >>$cfg
    fi
done
'''
                in k, k)

    def test_harness_api(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="harness=my-alternative-harness">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        k = recipe.installation.rendered_kickstart.kickstart
        self.assert_('beah' not in k, k)
        self.assert_('export BEAKER_LAB_CONTROLLER_URL="http://%s:8000/"'
                % self.lab_controller.fqdn in k, k)
        self.assert_('export BEAKER_LAB_CONTROLLER=%s' % self.lab_controller.fqdn in k, k)
        self.assert_('export BEAKER_RECIPE_ID=%s' % recipe.id in k, k)
        self.assert_('export BEAKER_HUB_URL="%s"' % get_server_base() in k, k)
        self.assert_('yum -y install my-alternative-harness' in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=978640
    def test_oats_api(self):
        # This is not a documented API at all, but OATS relies on 
        # LAB_CONTROLLER being defined in /etc/profile.d/rh-env.sh and we don't 
        # want to break that.
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        k = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('> /etc/profile.d/rh-env.sh\n'
                'export LAB_CONTROLLER=%s\n' % self.lab_controller.fqdn, k)

    def test_btrfs_volume(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="btrfs" name="mnt/testarea1" size="10" type="part"/>
                            <partition fs="btrfs" name="mnt/testarea2" size="10" type="part"/>
                        </partitions>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assertIn('''
part /boot --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
''',
                    recipe.installation.rendered_kickstart.kickstart)

        self.assertIn('''
part btrfs.mnt_testarea1 --size=10240
btrfs /mnt/testarea1 --label=mnt_testarea1 btrfs.mnt_testarea1
''',
                     recipe.installation.rendered_kickstart.kickstart)

        self.assertIn('''
part btrfs.mnt_testarea2 --size=10240
btrfs /mnt/testarea2 --label=mnt_testarea2 btrfs.mnt_testarea2
''',
                     recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1002261
    def test_btrfs_volume_rhel6(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="btrfs" name="mnt/testarea1" size="10" type="part"/>
                            <partition fs="btrfs" name="mnt/testarea2" size="10" type="part"/>
                        </partitions>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assertIn('''
part /boot --size 250 --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
''',
                    recipe.installation.rendered_kickstart.kickstart)

        self.assertIn('''
part /mnt/testarea1 --size=10240 --fstype btrfs
''',
                     recipe.installation.rendered_kickstart.kickstart)

        self.assertIn('''
part /mnt/testarea2 --size=10240 --fstype btrfs
''',
                     recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1088761
    def test_x86_efi_partition(self):
        efi_system = data_setup.create_system(arch=u'x86_64',
                status=u'Automated', lab_controller=self.lab_controller)
        efi_system.key_values_string.append(Key_Value_String(
                key=Key.by_name(u'NETBOOT_METHOD'), key_value=u'efigrub'))
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', efi_system)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart /boot/efi --fstype vfat --size 250 --recommended\n', ks)
        self.assertNotIn('\npart /boot ', ks)
        # also check when combined with ondisk
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="ondisk=vdb">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', efi_system)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart /boot/efi --fstype vfat --size 250 '
                '--recommended --ondisk=vdb\n', ks)
        self.assertNotIn('\npart /boot ', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1108393
    def test_x86_biosboot(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart biosboot --size 1 --fstype biosboot\n', ks)
        # also check when combined with ondisk
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="ondisk=vdb">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart biosboot --size 1 --fstype biosboot --ondisk=vdb\n', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1162513
    def test_ppc_prep_boot_partition(self):
        system = data_setup.create_system(arch=[u'ppc', u'ppc64', u'ppc64le'],
                status=u'Automated', lab_controller=self.lab_controller)
        for arch in [u'ppc', u'ppc64', u'ppc64le']:
            recipe = self.provision_recipe('''
                <job>
                    <whiteboard/>
                    <recipeSet>
                        <recipe>
                            <distroRequires>
                                <distro_name op="=" value="Fedora-rawhide" />
                                <distro_arch op="=" value="%s" />
                            </distroRequires>
                            <hostRequires/>
                            <partitions>
                                <partition fs="ext4" name="mnt" size="10" />
                            </partitions>
                            <task name="/distribution/install" />
                        </recipe>
                    </recipeSet>
                </job>
                ''' % arch, system)
            ks = recipe.installation.rendered_kickstart.kickstart
            self.assertIn('''
part None --fstype 'PPC PReP Boot' --size 8
part /boot --recommended --asprimary
''', ks)
            self.assertIn('\npart /mnt --size=10240 --fstype ext4\n', ks)
            # also check when combined with ondisk and fstype
            recipe = self.provision_recipe('''
                <job>
                    <whiteboard/>
                    <recipeSet>
                        <recipe ks_meta="ondisk=vdb fstype=ext4">
                            <distroRequires>
                                <distro_name op="=" value="Fedora-rawhide" />
                                <distro_arch op="=" value="%s" />
                            </distroRequires>
                            <hostRequires/>
                            <partitions/>
                            <task name="/distribution/install" />
                        </recipe>
                    </recipeSet>
                </job>
                ''' % arch, system)
            ks = recipe.installation.rendered_kickstart.kickstart
            self.assertIn('''
part None --fstype 'PPC PReP Boot' --size 8 --ondisk=vdb
part /boot --recommended --asprimary --fstype ext4 --ondisk=vdb
''', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1219965
    def test_aarch64_efi_partition(self):
        efi_system = data_setup.create_system(arch=u'aarch64',
                status=u'Automated', lab_controller=self.lab_controller)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="aarch64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', efi_system)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart /boot/efi --fstype vfat --recommended\n', ks)
        self.assertNotIn('\npart /boot ', ks)
        # also check when combined with ondisk
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="ondisk=vdb">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="aarch64" />
                        </distroRequires>
                        <hostRequires/>
                        <partitions>
                            <partition fs="ext4" name="mnt" size="10" />
                        </partitions>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', efi_system)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart /boot/efi --fstype vfat --recommended --ondisk=vdb\n', ks)
        self.assertNotIn('\npart /boot ', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1262098
    def test_boot_partition_size(self):
        # On RHEL7 and later we just use --recommended, for earlier RHELs that 
        # doesn't work so we have to supply a size.
        # We use fstype= here to trigger custom partitioning.
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=ext4">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assertIn('\npart /boot --recommended --asprimary --fstype ext4\n',
                recipe.installation.rendered_kickstart.kickstart)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=xfs">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assertIn('\npart /boot --recommended --asprimary --fstype xfs\n',
                recipe.installation.rendered_kickstart.kickstart)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=ext4">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assertIn('\npart /boot --size 250 --recommended --asprimary --fstype ext4\n',
                recipe.installation.rendered_kickstart.kickstart)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=ext3">
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assertIn('\npart /boot --size 250 --recommended --asprimary --fstype ext3\n',
                recipe.installation.rendered_kickstart.kickstart)
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="fstype=ext3">
                        <distroRequires>
                            <distro_name op="=" value="RHEL4-U9" />
                            <distro_variant op="=" value="AS" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        self.assertIn('\npart /boot --size 200 --recommended --asprimary --fstype ext3\n',
                recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=854229
    def test_swapsize(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="swapsize=2048">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('\npart swap --size 2048\n', ks)

    def test_anamon(self):
        # Test that we can override the anamon URL
        recipe_xml = '''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="anamon=http://example.com/myanamon">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            '''
        recipe = self.provision_recipe(recipe_xml, self.system)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('http://example.com/myanamon', ks)
        self.assertNotIn('http://lab.test-kickstart.invalid/beaker/anamon', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1029681
    def test_boot_order_manipulation_skipped_for_guest_recipes(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestargs="--ram=1024 vcpus=1">
                            <distroRequires>
                                <distro_name op="=" value="RHEL5-Server-U8" />
                                <distro_arch op="=" value="ia64" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" />
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="ia64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        guest = recipe.guests[0]
        ks = guest.installation.rendered_kickstart.kickstart
        self.assertNotIn('efibootmgr', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1063090
    def test_forcing_beah_version(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="beah_rpm=beah-0.6.48">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('yum -y install beah-0.6.48 ', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1065811
    def test_disable_ipv6_beah(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="beah_no_ipv6">
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="ia64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertEquals(ks.count('IPV6_DISABLED=True\n'), 2)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1099231
    def test_remote_post(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="remote_post=http://path/to/myscript">
                        <distroRequires>
                            <distro_name op="=" value="RHEL5-Server-U8" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('fetch remote_script http://path/to/myscript '
                      '&& chmod +x remote_script && ./remote_script',
                      ks)

        # Manual provision
        self.system.provisions[self.system.arch[0]] = Provision(arch=self.system.arch[0],
                                                                ks_meta=u'remote_post=http://path/to/myscript')
        tree = self.rhel62_server_x86_64
        install_options = self.system.manual_provision_install_options(tree)
        ks = generate_kickstart(install_options, tree, self.system, self.user).kickstart
        self.assertIn("fetch remote_script http://path/to/myscript "
                      "&& chmod +x remote_script && ./remote_script", ks.splitlines())

    # https://bugzilla.redhat.com/show_bug.cgi?id=1123700
    def test_systemd(self):
        distro_tree = data_setup.create_distro_tree(osmajor=u'CustomRHEL7',
                variant=u'Server', arch=u'x86_64',
                lab_controllers=[self.lab_controller])
        osmajor = distro_tree.distro.osversion.osmajor
        osmajor.install_options_by_arch[None] = OSMajorInstallOptions(ks_meta=u'systemd=True')
        session.flush()
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_family op="=" value="CustomRHEL7" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('export RHTS_OPTION_COMPATIBLE=\n', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1138533
    def test_guest_kickstarts_use_osmajor_default_install_options(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <guestrecipe>
                            <distroRequires>
                                <distro_name op="=" value="Fedora-18"/>
                                <distro_arch op="=" value="x86_64" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" />
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        guest = recipe.guests[0]
        ks = guest.installation.rendered_kickstart.kickstart
        self.assertIn('export RHTS_OPTION_COMPATIBLE=\n', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1138533
    def test_dynamic_virt_kickstarts_use_osmajor_default_install_options(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''', virt=True)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('export RHTS_OPTION_COMPATIBLE=\n', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1139951
    def test_guest_kickstarts_use_osmajor_custom_install_options(self):
        osmajor = OSMajor.by_name(u'Fedora18')
        osmajor.install_options_by_arch[None] = OSMajorInstallOptions(
                ks_meta=u'!has_systemd')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <guestrecipe>
                            <distroRequires>
                                <distro_name op="=" value="Fedora-18"/>
                                <distro_arch op="=" value="x86_64" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" />
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        guest = recipe.guests[0]
        ks = guest.installation.rendered_kickstart.kickstart
        self.assertNotIn('export RHTS_OPTION_COMPATIBLE=\n', ks)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1139951
    def test_dynamic_virt_kickstarts_use_osmajor_custom_install_options(self):
        osmajor = OSMajor.by_name(u'Fedora18')
        osmajor.install_options_by_arch[None] = OSMajorInstallOptions(
                ks_meta=u'!has_systemd')
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''', virt=True)
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertNotIn('export RHTS_OPTION_COMPATIBLE=\n', ks)

    #https://bugzilla.redhat.com/show_bug.cgi?id=1131388
    def test_contained_harness(self):
        # default
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="contained_harness selinux=--disabled">
                        <repos> <repo name="restraint" url="http://my/repo/"/> </repos>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        compare_expected('Fedora18-harness-contained', recipe.id,
                         recipe.installation.rendered_kickstart.kickstart)

        # Specify a custom image URL, harness entrypoint
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="contained_harness contained_harness_entrypoint=/usr/bin/mybinary harness_docker_base_image=docker-registry.mysys.com/fedora:latest selinux=--disabled">
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        compare_expected('Fedora18-harness-contained-custom', recipe.id,
                         recipe.installation.rendered_kickstart.kickstart)

        # Fedora rawhide host docker package name
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="contained_harness selinux=--disabled">
                        <repos> <repo name="restraint" url="http://my/repo/"/> </repos>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-rawhide" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)
        self.assertNotIn('\ndocker-io\n',
                      recipe.installation.rendered_kickstart.kickstart)
        self.assertIn('\ndocker\n',
                      recipe.installation.rendered_kickstart.kickstart)

    def test_disable_readahead_collection(self):
        # RHEL6, readahead collection disabled by default
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('READAHEAD_COLLECT="no"', ks)

        # RHEL7, readahead collection disabled by default
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('disable systemd-readahead-collect', ks)

        # no_disable_readahead
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="no_disable_readahead">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-7.0-20120314.0" />
                            <distro_variant op="=" value="Workstation" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>''')
        ks = recipe.installation.rendered_kickstart.kickstart
        self.assertNotIn('disable systemd-readahead-collect', ks)
        self.assertNotIn('READAHEAD_COLLECT="no"', ks)


    def test_provision_rpmostree(self):
        recipe = self.provision_recipe('''
        <job>
            <whiteboard/>
            <recipeSet>
                <recipe ks_meta="ostree_repo_url=http://foo/bar/repo ostree_ref=my/remote/ref harness_docker_base_image=registry.hub.docker.com/fedora:20 selinux=--disabled">
                   <repos> <repo name="restraint" url="http://my/repo/"/> </repos>2728
                   <distroRequires>
                       <distro_name op="=" value="Atomic-Host" />
                       <distro_arch op="=" value="x86_64" />
                   </distroRequires>
                   <hostRequires/>
                  <task name="/distribution/install" />
                </recipe>
            </recipeSet>
        </job>
        ''', self.system)
        compare_expected('AtomicHost-defaults', recipe.id,
                    recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1198881
    def test_no_autopart(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe ks_meta="no_autopart">
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                            <distro_variant op="=" value="Server" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <ks_appends>
                            <ks_append>
part raid.01 --size=20480 --ondisk=sda
part raid.02 --size=20480 --ondisk=sdb
part raid.03 --size=20480 --ondisk=sdc
volgroup bootvg --pesize=32768 pv.01
                            </ks_append>
                        </ks_appends>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system)

        self.assertNotIn('autopart',
                      recipe.installation.rendered_kickstart.kickstart)
        part_lines = [r'''part raid.01 --size=20480 --ondisk=sda''',
                      r'''part raid.02 --size=20480 --ondisk=sdb''',
                      r'''part raid.03 --size=20480 --ondisk=sdc''',
                      r'''volgroup bootvg --pesize=32768 pv.01''']
        for line in part_lines:
            self.assert_(line in recipe.installation.rendered_kickstart.kickstart.splitlines(),
                         recipe.installation.rendered_kickstart.kickstart)

    # https://bugzilla.redhat.com/show_bug.cgi?id=1255210
    def test_systemctl_service_suffix(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-18" />
                            <distro_arch op="=" value="x86_64" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''')
        k = recipe.installation.rendered_kickstart.kickstart
        self.assertIn('systemctl enable beah-srv.service', k)
        self.assertIn('systemctl enable beah-beaker-backend.service', k)
        self.assertIn('systemctl enable beah-fwd-backend.service', k)
