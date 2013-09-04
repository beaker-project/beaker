
import unittest2 as unittest
import urlparse
import tempfile
import re
import pkg_resources
import pipes
import jinja2
import xmltramp
import crypt
from bkr.server import model
from bkr.server.model import session, DistroTreeRepo, LabControllerDistroTree, \
        CommandActivity, Provision, SSHPubKey, ProvisionFamily, OSMajor, Arch
from bkr.server.kickstart import template_env, generate_kickstart
from bkr.server.jobs import Jobs
from bkr.server.jobxml import XmlJob
from bkr.inttest import data_setup, get_server_base, with_transaction, \
        DummyVirtManager

def compare_expected(name, recipe_id, actual):
    expected = pkg_resources.resource_string('bkr.inttest',
            'server/kickstarts/%s.expected' % name)
    # Unfortunately there are a few things that vary for each test run,
    # so we have to substitute them:
    vars = {
        '@RECIPEID@': str(recipe_id),
        '@BEAKER@': get_server_base(),
        '@REPOS@': urlparse.urljoin(get_server_base(), '/repos/'),
        '@HARNESS@': urlparse.urljoin(get_server_base(), '/harness/'),
    }
    for var, value in vars.iteritems():
        expected = expected.replace(var, value)
    if expected != actual:
        expected_path = pkg_resources.resource_filename('bkr.inttest',
                'server/kickstarts/%s.expected' % name)
        # Undo the substitutions, so that we get a sensible diff
        actual = re.sub(r'\b%s\b' % vars.pop('@RECIPEID@'), '@RECIPEID@', actual)
        for var, value in vars.iteritems():
            actual = actual.replace(value, var)
        actual_temp = tempfile.NamedTemporaryFile(prefix='beaker-kickstart-test-',
                suffix='-actual', delete=False)
        actual_temp.write(actual)
        raise AssertionError('actual kickstart does not match expected\n'
                'diff -u %s %s\nmv %s %s' % (expected_path, actual_temp.name,
                actual_temp.name, expected_path))

class KickstartTest(unittest.TestCase):

    maxDiff = None

    @classmethod
    @with_transaction
    def setUpClass(cls):
        cls.orig_template_loader = template_env.loader
        template_env.loader = jinja2.ChoiceLoader([cls.orig_template_loader,
                jinja2.DictLoader({
                    'snippets/per_lab/lab_env/lab.test-kickstart.invalid': '''
cat << EOF > /etc/profile.d/rh-env.sh
export LAB_CONTROLLER=lab.test-kickstart.invalid
export DUMPSERVER=netdump.test-kickstart.invalid
export NFSSERVERS="RHEL3,rhel3-nfs.test-kickstart.invalid:/export/home RHEL4,rhel4-nfs.test-kickstart.invalid:/export/home RHEL5,rhel5-nfs.test-kickstart.invalid:/export/home RHEL6,rhel6-nfs.test-kickstart.invalid:/export/home NETAPP, SOLARIS,"
export LOOKASIDE=http://download.test-kickstart.invalid/lookaside/
export BUILDURL=http://download.test-kickstart.invalid
EOF
cat << EOF > /etc/profile.d/rh-env.csh
setenv LAB_CONTROLLER lab.test-kickstart.invalid
setenv DUMPSERVER netdump.test-kickstart.invalid
setenv NFSSERVERS "RHEL3,rhel3-nfs.test-kickstart.invalid:/export/home RHEL4,rhel4-nfs.test-kickstart.invalid:/export/home RHEL5,rhel5-nfs.test-kickstart.invalid:/export/home RHEL6,rhel6-nfs.test-kickstart.invalid:/export/home NETAPP, SOLARIS,"
setenv LOOKASIDE http://download.test-kickstart.invalid/lookaside/
setenv BUILDURL http://download.test-kickstart.invalid
EOF
''',
                    'snippets/per_system/packages/bz728410-system-with-packages':
                        'special-weird-driver-package\n',
                })])
        cls.orig_VirtManager = model.VirtManager
        model.VirtManager = DummyVirtManager

        cls.lab_controller = data_setup.create_labcontroller(
                fqdn=u'lab.test-kickstart.invalid')
        cls.system = data_setup.create_system(arch=u'x86_64',
                fqdn=u'test01.test-kickstart.invalid', status=u'Automated',
                lab_controller=cls.lab_controller)
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
                distro=cls.rhel58server, variant=None, arch=u'x86_64',
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

        cls.rhel62 = data_setup.create_distro(name=u'RHEL-6.2',
                osmajor=u'RedHatEnterpriseLinux6', osminor=u'2')
        cls.rhel62_server_x86_64 = data_setup.create_distro_tree(
                distro=cls.rhel62, variant=u'Server', arch=u'x86_64',
                lab_controllers=[cls.lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/x86_64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-6.2/Server/x86_64/os/'])
        cls.rhel62_server_x86_64.repos[:] = [
            DistroTreeRepo(repo_id=u'HighAvailability', repo_type=u'addon',
                    path=u'HighAvailability'),
            DistroTreeRepo(repo_id=u'LoadBalancer', repo_type=u'addon',
                    path=u'LoadBalancer'),
            DistroTreeRepo(repo_id=u'ResilientStorage', repo_type=u'addon',
                    path=u'ResilientStorage'),
            DistroTreeRepo(repo_id=u'ScalableFileSystem', repo_type=u'addon',
                    path=u'ScalableFileSystem'),
            DistroTreeRepo(repo_id=u'Server', repo_type=u'os', path=u'Server'),
            DistroTreeRepo(repo_id=u'optional-x86_64-os', repo_type=u'addon',
                    path=u'../../optional/x86_64/os'),
            DistroTreeRepo(repo_id=u'debug', repo_type=u'debug',
                    path=u'../debug'),
            DistroTreeRepo(repo_id=u'optional-x86_64-debug', repo_type=u'debug',
                    path=u'../../optional/x86_64/debug'),
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
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-7.0-20120314.0/compose/Workstation/x86_64/os/'])
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

        session.flush()

    def setUp(self):
        session.begin()
        self.user = data_setup.create_user(password=u'password')
        self.user.root_password = '$1$beaker$yMeLK4p1IVkFa80RyTkpE.'

    def tearDown(self):
        session.rollback()

    @classmethod
    def tearDownClass(cls):
        model.VirtManager = cls.orig_VirtManager
        template_env.loader = cls.orig_template_loader

    def provision_recipe(self, xml, system=None, virt=False):
        """
        Pass either system, or virt=True.
        """
        xmljob = XmlJob(xmltramp.parse(xml))
        job = Jobs().process_xmljob(xmljob, self.user)
        recipe = job.recipesets[0].recipes[0]
        session.flush()
        data_setup.mark_recipe_waiting(recipe, system=system,
                virt=virt, lab_controller=self.lab_controller)
        recipe.provision()
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
                recipe.rendered_kickstart.kickstart)

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
                      recipe.rendered_kickstart.kickstart)

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
                recipe.rendered_kickstart.kickstart)

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
                     recipe.rendered_kickstart.kickstart)

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
                recipe.rendered_kickstart.kickstart)

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
                      recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

        for line in recipe.rendered_kickstart.kickstart.splitlines():
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
                recipe.rendered_kickstart.kickstart)

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
                      recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

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
                       r'''part /boot --size 200 --recommended --asprimary --ondisk=/dev/sda''',
                       r'''part / --size 1024 --grow --ondisk=/dev/sda''',
                       r'''part swap --recommended --ondisk=/dev/sda''']

        for line in ondisk_lines:
            self.assert_(line in recipe.rendered_kickstart.kickstart.splitlines(),
                         recipe.rendered_kickstart.kickstart)

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

        part_lines = [r'''part /boot --size 200 --recommended --asprimary''',
                      r'''part / --size 1024 --grow''',
                      r'''part swap --recommended''',
                      r'''part /home --size=5120 --fstype ext4''']

        for line in part_lines:
            self.assert_(line in recipe.rendered_kickstart.kickstart.splitlines(),
                         recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)


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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

        self.assert_(r'''xconfig''' not in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

        self.assert_(r'''vmcp ipl''' in recipe.rendered_kickstart.kickstart,
                     recipe.rendered_kickstart.kickstart)


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

        self.assert_(r'''unsupported_hardware''' in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

    def test_rhel6_guest_console(self):
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <guestrecipe guestargs="--ram=1024 vcpus=1">
                            <distroRequires>
                                <distro_name op="=" value="RHEL-6.2" />
                            </distroRequires>
                            <hostRequires/>
                            <task name="/distribution/install" />
                            <task name="/distribution/reservesys" />
                        </guestrecipe>
                        <distroRequires>
                            <distro_name op="=" value="RHEL-6.2" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                        <task name="/distribution/reservesys" />
                    </recipe>
                </recipeSet>
            </job>''')
        guest = recipe.guests[0]
        data_setup.mark_recipe_waiting(guest)
        guest.provision()
        ks = guest.rendered_kickstart.kickstart
        self.assert_(r'''bootloader --location=mbr  --append="console=ttyS0,115200 console=ttyS1,115200"''' in ks.splitlines(), ks)
        self.assert_('cat << EOF >/etc/init/ttyS0.conf\n'
            '# start ttyS0\nstart on runlevel [2345]\n'
            'stop on runlevel [S016]\ninstance ttyS0\n'
            'respawn\npre-start exec /sbin/securetty ttyS0\n'
            'exec /sbin/agetty /dev/ttyS0 115200 vt100-nav\nEOF\n'
            '\ncat << EOF >/etc/init/ttyS1.conf\n'
            '# start ttyS1\nstart on runlevel [2345]\nstop on runlevel [S016]\n'
            'instance ttyS1\nrespawn\npre-start exec /sbin/securetty ttyS1\n'
            'exec /sbin/agetty /dev/ttyS1 115200 vt100-nav\nEOF\n' in ks, ks)

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
                recipe.rendered_kickstart.kickstart)

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
                      recipe.rendered_kickstart.kickstart)

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
                         recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

        self.assert_(r'''xconfig''' not in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

        self.assert_(r'''vmcp ipl''' not in recipe.rendered_kickstart.kickstart,
                     recipe.rendered_kickstart.kickstart)

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
                recipe.rendered_kickstart.kickstart)

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
                     recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.splitlines(),
                     recipe.rendered_kickstart.kickstart)

    def test_job_group_password(self):
        group = data_setup.create_group(group_name='group1', root_password='blappy7')
        self.user.groups.append(group)
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
                'rootpw --iscrypted %s' % group.root_password
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)



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
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
                         recipe.rendered_kickstart.kickstart)

    def test_leavebootorder(self):
        system = data_setup.create_system(arch=u'ppc64', status=u'Automated',
                lab_controller=self.lab_controller)
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
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
        self.assert_(
                r'''    /bin/sed -i 's/^\(serial.*\)--unit=\S\+\(.*\)$/\1--port=0x02f8\2/' /boot/grub/grub.conf'''
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

        self.assert_(
                r'''    /bin/sed -i '/^GRUB_SERIAL_COMMAND="serial/ {s/--unit=[0-9]\+//; s/"$/ --port=0x02f8"/}' /etc/default/grub'''
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
        self.assert_('device scsi cciss' in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
        self.assert_('device cciss' in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
                in recipe.rendered_kickstart.kickstart.splitlines(),
                recipe.rendered_kickstart.kickstart)

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
part /boot --size 200 --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
part pv.001 --size=25605
volgroup TestVolume001 pv.001
logvol /butter --name=butter --vgname=TestVolume001 --size=25600 --fstype btrfs
'''
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

    def test_sshkeys_group(self):
        self.user.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'neveroddoreven', u'description'))
        user2 = data_setup.create_user()
        user2.sshpubkeys.append(SSHPubKey(u'ssh-rsa', u'murderforajarofredrum', u'description'))
        group = data_setup.create_group(group_name=data_setup.unique_name('group%s'))
        self.user.groups.append(group)
        user2.groups.append(group)
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
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

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
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

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
                     in recipe.rendered_kickstart.kickstart.split('cat >>/root/.ssh/authorized_keys')[1],
                     recipe.rendered_kickstart.kickstart)

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
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

    def test_custom_kickstart(self):
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
        k = recipe.rendered_kickstart.kickstart
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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('ssh-rsa lolthisismykey description' in k.splitlines(), k)

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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('repo --name=beaker-debug' not in k, k)
        self.assert_('repo --name=beaker-optional-x86_64-debug' not in k, k)
        self.assert_('/etc/yum.repos.d/beaker-debug.repo' not in k, k)
        self.assert_('/etc/yum.repos.d/beaker-optional-x86_64-debug.repo' not in k, k)

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
        k = recipe.rendered_kickstart.kickstart
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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('export BEAKER="%s"' % get_server_base() in k, k)

    # https://bugzilla.redhat.com/show_bug.cgi?id=691442
    def test_whiteboards(self):
        # This test checks that the job and recipe whiteboards are made
        # available in the test environments via the kickstart templates
        whiteboard = '''
            This
            Is
            A
            Multi-line
            Whiteboard
            Entry
            With "embedded double quotes"
            And 'embedded single quotes'
        '''
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
        # The XML processing normalises whitespace for the job level
        # whiteboard element, but only replaces the line breaks with
        # spaces for the recipe level whiteboard attribute
        # This test just checks for that currently expected behaviour
        # without passing too much judgment on its sanity...
        job_lines = (line.strip() for line in whiteboard.splitlines())
        job_entry = "Job: " + " ".join(line for line in job_lines if line)
        recipe_entry = ("Recipe: " +
                        " ".join(line for line in whiteboard.splitlines()))
        recipe = self.provision_recipe(recipe_xml, self.system)
        recipe_whiteboard = recipe.whiteboard
        self.assertEqual(recipe_whiteboard, recipe_entry)
        job_whiteboard = recipe.recipeset.job.whiteboard
        self.assertEqual(job_whiteboard, job_entry)
        recipe_quoted = pipes.quote(recipe_entry)
        job_quoted = pipes.quote(job_entry)
        ks = recipe.rendered_kickstart.kickstart
        self.assert_('export BEAKER_JOB_WHITEBOARD=%s'
                           % job_quoted in ks, ks)
        self.assert_('export BEAKER_RECIPE_WHITEBOARD=%s'
                           % recipe_quoted in ks, ks)
        self.assert_('setenv BEAKER_JOB_WHITEBOARD %s'
                           % job_quoted in ks, ks)
        self.assert_('setenv BEAKER_RECIPE_WHITEBOARD %s'
                           % recipe_quoted in ks, ks)

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
        ks = recipe.rendered_kickstart.kickstart
        self.assert_("export BEAKER_JOB_WHITEBOARD=''" in ks, ks)
        self.assert_("export BEAKER_RECIPE_WHITEBOARD=''" in ks, ks)
        self.assert_("setenv BEAKER_JOB_WHITEBOARD ''" in ks, ks)
        self.assert_("setenv BEAKER_RECIPE_WHITEBOARD ''" in ks, ks)

    def test_no_recipe(self):
        # This test checks that everything works as expected with no
        # recipe defined at all (which can happen when systems are
        # switched to manual mode instead of automatic)
        tree = self.rhel62_server_x86_64
        ks = generate_kickstart(self.system.install_options(tree),
                                tree, self.system, None).kickstart
        self.assert_("export BEAKER_JOB_WHITEBOARD=''" in ks, ks)
        self.assert_("export BEAKER_RECIPE_WHITEBOARD=''" in ks, ks)
        self.assert_("setenv BEAKER_JOB_WHITEBOARD ''" in ks, ks)
        self.assert_("setenv BEAKER_RECIPE_WHITEBOARD ''" in ks, ks)

    def test_no_system_or_recipe(self):
        # We need one or the other in order to find the lab controller
        tree = self.rhel62_server_x86_64
        self.assertRaises(ValueError, generate_kickstart,
                          self.system.install_options(tree),
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
        k = recipe.rendered_kickstart.kickstart
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
        for line in recipe.rendered_kickstart.kickstart.split('\n'):
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
part /boot --size 200 --recommended --asprimary
part / --size 1024 --grow --fstype btrfs
part swap --recommended

'''
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

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
part /boot --size 200 --recommended --asprimary --fstype ext4
part / --size 1024 --grow --fstype ext4
part swap --recommended

'''
                in recipe.rendered_kickstart.kickstart,
                recipe.rendered_kickstart.kickstart)

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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('''
network --bootproto=dhcp
network --bootproto=static --device=00:11:22:33:44:55 --ip=192.168.99.1 --netmask=255.255.255.0
network --bootproto=static --device=66:77:88:99:aa:bb --ip=192.168.100.1 --netmask=255.255.255.0
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
        k = recipe.rendered_kickstart.kickstart
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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('# Install U-Boot boot.scr' in k.splitlines(), k)
        self.assert_('Yosemite Fedora' in k, k)

    def test_f17_arm(self):
        # Fedora 17 ARM had some special one-off hacks
        recipe = self.provision_recipe('''
            <job>
                <whiteboard/>
                <recipeSet>
                    <recipe>
                        <distroRequires>
                            <distro_name op="=" value="Fedora-17" />
                            <distro_arch op="=" value="armhfp" />
                        </distroRequires>
                        <hostRequires/>
                        <task name="/distribution/install" />
                    </recipe>
                </recipeSet>
            </job>
            ''', self.system_armhfp)
        k = recipe.rendered_kickstart.kickstart
        self.assert_('http://dmarlin.fedorapeople.org/yum/f17/arm/os/Packages/' in k, k)
        self.assert_('%packages --ignoremissing\nuboot-tools' in k, k)

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
        k = recipe.rendered_kickstart.kickstart
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
        k = recipe.rendered_kickstart.kickstart
        kickstart_lines = k.splitlines()
        self.assert_(kickstart_lines.count('requires1') == 1)

    def test_postreboot_for_rhev_guests(self):
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
            ''', virt=True)
        k = recipe.rendered_kickstart.kickstart
        self.assert_(('curl http://lab.test-kickstart.invalid:8000/postreboot/%s'
                % recipe.id) in k.splitlines(), k)

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
        k = recipe.rendered_kickstart.kickstart
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
        k = recipe.rendered_kickstart.kickstart
        self.assert_('beah' not in k, k)
        self.assert_('export BEAKER_LAB_CONTROLLER_URL="http://%s:8000/"'
                % self.lab_controller.fqdn in k, k)
        self.assert_('export BEAKER_LAB_CONTROLLER=%s' % self.lab_controller.fqdn in k, k)
        self.assert_('export BEAKER_RECIPE_ID=%s' % recipe.id in k, k)
        self.assert_('export BEAKER_HUB_URL="%s"' % get_server_base() in k, k)
        self.assert_('yum -y install my-alternative-harness' in k, k)

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
part /boot --size 200 --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
''',
                    recipe.rendered_kickstart.kickstart)

        self.assertIn('''
part btrfs.mnt_testarea1 --size=10240
btrfs /mnt/testarea1 --label=mnt_testarea1 btrfs.mnt_testarea1
''',
                     recipe.rendered_kickstart.kickstart)

        self.assertIn('''
part btrfs.mnt_testarea2 --size=10240
btrfs /mnt/testarea2 --label=mnt_testarea2 btrfs.mnt_testarea2
''',
                     recipe.rendered_kickstart.kickstart)

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
part /boot --size 200 --recommended --asprimary
part / --size 1024 --grow
part swap --recommended
''',
                    recipe.rendered_kickstart.kickstart)

        self.assertIn('''
part /mnt/testarea1 --size=10240 --fstype btrfs
''',
                     recipe.rendered_kickstart.kickstart)

        self.assertIn('''
part /mnt/testarea2 --size=10240 --fstype btrfs
''',
                     recipe.rendered_kickstart.kickstart)
