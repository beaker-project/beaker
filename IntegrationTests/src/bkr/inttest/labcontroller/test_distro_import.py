import os
import unittest
import subprocess
import json
import pkg_resources
from copy import copy
from bkr.inttest import Process
from bkr.server.model import OSMajor
from turbogears.database import session

_current_dir = os.path.dirname(__file__)
_compose_test_dir = pkg_resources.resource_filename('bkr.inttest.labcontroller', 'compose_layout')
_git_root_dir = os.path.join(_current_dir, '..', '..', '..', '..', '..')

if os.path.exists(os.path.join(_git_root_dir, '.git')):
    # Looks like we are in a git checkout
    _command = os.path.join(_git_root_dir, 'LabController/src/bkr/labcontroller/distro_import.py')
else:
    _command = '/usr/bin/beaker-import'

class TreeImportError(Exception):

    def __init__(self, command, status, stderr_output):
        Exception.__init__(self, 'Distro import failed: %r '
                           'with exit status %s:\n%s' % (command, status, stderr_output))
        self.status = status
        self.stderr_output = stderr_output

class DistroImportTest(unittest.TestCase):

    maxDiff = None

    @classmethod
    def setupClass(cls):
        cls.distro_server = Process('http_server.py',
                args=['python', os.path.join(_current_dir, '..', 'http_server.py'),],
                listen_port=19998, exec_dir=_compose_test_dir)
        cls.distro_server.start()
        cls.distro_url = 'http://localhost:19998/'

    @classmethod
    def teardownClass(cls):
        cls.distro_server.stop()

    def setUp(self):
        self.import_args = ['python', _command, '--dry-run', '--quiet', '--json']

        self.i386_rhel4 = {u'arch': u'i386',
                          u'arches': [],
                          u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                                      {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
                          u'kernel_options': None,
                          u'kernel_options_post': None,
                          u'ks_meta': None,
                          u'name': u'RHEL4-U9',
                          u'osmajor': u'RedHatEnterpriseLinux4',
                          u'osminor': u'9',
                          u'repos': [{u'path': u'../repo-debug-AS-i386',
                                      u'repoid': u'AS-debuginfo',
                                      u'type': u'debug'},
                                     {u'path': u'../repo-AS-i386',
                                      u'repoid': u'AS',
                                      u'type': u'variant'}],
                          u'tree_build_time': 0.0,
                          u'tags': [u'RELEASED'],
                          u'urls': [u'http://localhost:19998/RHEL-4/U9/AS/i386/tree/'],
                          u'variant': u'AS'}

        self.x86_64_rhel5 = {u'osmajor': u'RedHatEnterpriseLinuxServer5',
                            u'tree_build_time': u'1352937955.19',
                            u'name': u'RHEL5.9-Server-20121114.2',
                            u'kernel_options_post': None,
                            u'tags': [u'RHEL-5.9-Server-RC-1.0'],
                            u'repos': [{u'path': u'VT',
                                        u'type': u'addon',
                                        u'repoid': u'VT'},
                                      {u'path': u'Server',
                                       u'type': u'addon',
                                       u'repoid': u'Server'},
                                      {u'path': u'Cluster',
                                       u'type': u'addon',
                                       u'repoid': u'Cluster'},
                                      {u'path': u'ClusterStorage',
                                       u'type': u'addon',
                                       u'repoid': u'ClusterStorage'},
                                      {u'path': u'../debug',
                                       u'type': u'debug',
                                       u'repoid': u'debuginfo'}],
                            u'variant': u'',
                            u'kernel_options': None,
                            u'arches': [],
                            u'urls': [u'http://localhost:19998/RHEL5-Server/x86_64/os/'],
                            u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                         u'type': u'kernel'},
                                        {u'path': u'images/pxeboot/initrd.img',
                                         u'type': u'initrd'}],
                            u'arch': u'x86_64',
                            u'osminor': u'9',
                            u'ks_meta': None}

        self.i386_rhel5 = {u'osmajor': u'RedHatEnterpriseLinuxServer5',
                          u'name': u'RHEL5.9-Server-20121114.2',
                          u'tree_build_time': u'1352936114.36',
                          u'kernel_options_post': None,
                          u'tags': [u'RHEL-5.9-Server-RC-1.0'],
                          u'repos': [{u'path': u'VT',
                                      u'type': u'addon',
                                      u'repoid': u'VT'},
                                     {u'path': u'Server',
                                      u'type': u'addon',
                                      u'repoid': u'Server'},
                                     {u'path': u'Cluster',
                                      u'type': u'addon',
                                      u'repoid': u'Cluster'},
                                     {u'path': u'ClusterStorage',
                                      u'type': u'addon',
                                      u'repoid': u'ClusterStorage'},
                                     {u'path': u'../debug',
                                      u'type': u'debug',
                                      u'repoid': u'debuginfo'}],
                          u'variant': u'',
                          u'kernel_options': None,
                          u'arches': [],
                          u'urls': [u'http://localhost:19998/RHEL5-Server/i386/os/'],
                          u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                       u'type': u'kernel'},
                                      {u'path': u'images/pxeboot/initrd.img',
                                       u'type': u'initrd'}],
                          u'arch': u'i386',
                          u'osminor': u'9',
                          u'ks_meta': None}

        self.x86_64_rhel6 = {u'osmajor': u'RedHatEnterpriseLinux6',
                            u'name': u'RHEL6.4-20130130.0',
                            u'tree_build_time' : u'1285193176.460470',
                            u'osminor': u'0',
                            u'tags': [],
                            u'kernel_options_post': None,
                            u'repos': [{u'path': u'Server',
                                        u'type': u'variant',
                                        u'repoid': u'Server'},
                                       {u'path': u'ResilientStorage',
                                        u'type': u'addon',
                                        u'repoid': u'ResilientStorage'},
                                       {u'path': u'HighAvailability',
                                        u'type': u'addon',
                                        u'repoid': u'HighAvailability'},
                                       {u'path': u'ScalableFileSystem',
                                        u'type': u'addon',
                                        u'repoid': u'ScalableFileSystem'},
                                       {u'path': u'LoadBalancer',
                                        u'type': u'addon',
                                        u'repoid': u'LoadBalancer'},
                                       {u'path': u'../debug',
                                        u'type': u'debug',
                                        u'repoid': u'debuginfo'},
                                       {u'path': u'../../optional/x86_64/debug',
                                        u'type': u'debug',
                                        u'repoid': u'optional-debuginfo'},
                                       {u'path': u'../../optional/x86_64/os',
                                        u'type': u'optional',
                                        u'repoid': u'optional'}],
                            u'variant': u'Server',
                            u'kernel_options': None,
                            u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                         u'type': u'kernel'},
                                        {u'path': u'images/pxeboot/initrd.img',
                                         u'type': u'initrd'}],
                            u'arches': [],
                            u'urls': [u'http://localhost:19998/RHEL6-Server/x86_64/os/'],
                            u'arch': u'x86_64',
                            u'ks_meta': None}

        self.i386_rhel6 = {u'osmajor': u'RedHatEnterpriseLinux6',
                          u'name': u'RHEL6.4-20130130.0',
                          u'tree_build_time': u'1285191262.134687',
                          u'kernel_options_post': None,
                          u'tags': [],
                          u'repos': [{u'path': u'Server', u'type': u'variant',
                                      u'repoid': u'Server'},
                                     {u'path': u'ResilientStorage',
                                      u'type': u'addon',
                                      u'repoid': u'ResilientStorage'},
                                     {u'path': u'HighAvailability',
                                      u'type': u'addon',
                                      u'repoid': u'HighAvailability'},
                                     {u'path': u'LoadBalancer',
                                      u'type': u'addon',
                                      u'repoid': u'LoadBalancer'},
                                     {u'path': u'../debug', u'type': u'debug',
                                      u'repoid': u'debuginfo'},
                                     {u'path': u'../../optional/i386/debug',
                                      u'type': u'debug',
                                      u'repoid': u'optional-debuginfo'},
                                     {u'path': u'../../optional/i386/os',
                                      u'type': u'optional', u'repoid': u'optional'}],
                          u'variant': u'Server',
                          u'kernel_options': None,
                          u'arches': [],
                          u'urls': [u'http://localhost:19998/RHEL6-Server/i386/os/'],
                          u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                       u'type': u'kernel'},
                                      {u'path': u'images/pxeboot/initrd.img',
                                       u'type': u'initrd'}],
                          u'arch': u'i386',
                          u'osminor': u'0',
                          u'ks_meta': None}

        self.x86_64_rhel7_compose = {u'arch': u'x86_64',
                                    u'arches': [],
                                    u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                                                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
                                    u'kernel_options': None,
                                    u'kernel_options_post': None,
                                    u'ks_meta': None,
                                    u'name': u'RHEL-7.0-20120711.2',
                                    u'osmajor': u'RedHatEnterpriseLinux7',
                                    u'osminor': u'0',
                                    u'repos': [{u'path': u'addons/ScalableFileSystem',
                                                u'repoid': u'ScalableFileSystem',
                                                u'type': u'addon'},
                                               {u'path': u'../../../Workstation-optional/x86_64/os',
                                                u'repoid': u'Workstation-optional',
                                                u'type': u'optional'},
                                               {u'path': u'../../../Workstation-optional/x86_64/debuginfo/tree',
                                                u'repoid': u'Workstation-optional-debuginfo',
                                                u'type': u'debug'},
                                               {u'path': u'../../../Workstation/x86_64/os',
                                                u'repoid': u'Workstation',
                                                u'type': u'variant'},
                                               {u'path': u'../../../Workstation/x86_64/debuginfo/tree',
                                                u'repoid': u'Workstation-debuginfo',
                                                u'type': u'debug'}],
                                    u'tags': [],
                                    u'tree_build_time': u'1342048152.161907',
                                    u'urls': [u'http://localhost:19998/RHEL7/Workstation/x86_64/os/'],
                                    u'variant': u'Workstation'}

        self.s390x_rhel7_compose= {u'arch': u's390x',
                                   u'arches': [],
                                   u'images': [{u'path': u'images/kernel.img', u'type': u'kernel'},
                                               {u'path': u'images/initrd.img', u'type': u'initrd'}],
                                   u'kernel_options': None,
                                   u'kernel_options_post': None,
                                   u'ks_meta': None,
                                   u'name': u'RHEL-7.0-20120711.2',
                                   u'osmajor': u'RedHatEnterpriseLinux7',
                                   u'osminor': u'0',
                                   u'repos': [{u'path': u'../../../Server-optional/s390x/os',
                                               u'repoid': u'Server-optional',
                                               u'type': u'optional'},
                                              {u'path': u'../../../Server-optional/s390x/debuginfo/tree',
                                               u'repoid': u'Server-optional-debuginfo',
                                               u'type': u'debug'},
                                              {u'path': u'../../../Server/s390x/os',
                                               u'repoid': u'Server',
                                               u'type': u'variant'},
                                              {u'path': u'../../../Server/s390x/debuginfo/tree',
                                               u'repoid': u'Server-debuginfo',
                                               u'type': u'debug'}],
                                   u'tags': [],
                                   u'tree_build_time': u'1342048144.836192',
                                   u'urls': [u'http://localhost:19998/RHEL7/Server/s390x/os/'],
                                   u'variant': u'Server'}

        self.ppc64_rhel7_compose = { u'arch': u'ppc64',
                                     u'arches': [],
                                     u'images': [{u'path': u'ppc/ppc64/vmlinuz', u'type': u'kernel'},
                                                 {u'path': u'ppc/ppc64/initrd.img', u'type': u'initrd'}],
                                     u'kernel_options': None,
                                     u'kernel_options_post': None,
                                     u'ks_meta': None,
                                     u'name': u'RHEL-7.0-20120711.2',
                                     u'osmajor': u'RedHatEnterpriseLinux7',
                                     u'osminor': u'0',
                                     u'repos': [{u'path': u'../../../Server-optional/ppc64/os',
                                                 u'repoid': u'Server-optional',
                                                 u'type': u'optional'},
                                                {u'path': u'../../../Server-optional/ppc64/debuginfo/tree',
                                                 u'repoid': u'Server-optional-debuginfo',
                                                 u'type': u'debug'},
                                                {u'path': u'../../../Server/ppc64/os',
                                                 u'repoid': u'Server',
                                                 u'type': u'variant'},
                                                {u'path': u'../../../Server/ppc64/debuginfo/tree',
                                                 u'repoid': u'Server-debuginfo',
                                                 u'type': u'debug'}],
                                     u'tags': [],
                                     u'tree_build_time': u'1342048133.432813',
                                     u'urls': [u'http://localhost:19998/RHEL7/Server/ppc64/os/'],
                                     u'variant': u'Server'}


        # separate expected tree data are maintained for import from .treeinfo
        # and .composeinfo, since Fedora's composeingo has debuginfo information
        # but, .treeinfo doesn't. See the sample files in compose_layout/ for examples

        self.x86_64_f17 = {u'osmajor': u'Fedora17',
                           u'name': u'Fedora-17',
                           u'tree_build_time': u'1337720130.41',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [{u'path': u'../../../Everything/x86_64/os',
                                       u'repoid': u'Fedora-Everything',
                                       u'type': u'fedora'},
                                      {u'path': u'../debug', u'type': u'debug',
                                       u'repoid': u'Fedora-debuginfo'}],
                           u'variant': u'Fedora',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-17/GOLD/Fedora/x86_64/os/'],
                           u'arch': u'x86_64',
                           u'ks_meta': None}

        self.i386_f17 = {u'osmajor': u'Fedora17',
                         u'name': u'Fedora-17',
                         u'tree_build_time': u'1337720321.88',
                         u'osminor': u'0',
                         u'tags': [],
                         u'kernel_options_post': None,
                         u'repos': [{u'path': u'../../../Everything/i386/os',
                                     u'repoid': u'Fedora-Everything',
                                     u'type': u'fedora'},
                                    {u'path': u'../debug', u'type': u'debug',
                                     u'repoid': u'Fedora-debuginfo'}],
                         u'variant': u'Fedora',
                         u'kernel_options': None,
                         u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                      u'type': u'kernel'},
                                     {u'path': u'images/pxeboot/initrd.img',
                                      u'type': u'initrd'}],
                         u'arches': [],
                         u'urls': [u'http://localhost:19998/F-17/GOLD/Fedora/i386/os/'],
                         u'arch': u'i386',
                         u'ks_meta': None}

        self.x86_64_f17_compose = {u'osmajor': u'Fedora17',
                                   u'name': u'Fedora-17',
                                   u'tree_build_time': u'1337720130.41',
                                   u'osminor': u'0',
                                   u'tags': [],
                                   u'kernel_options_post': None,
                                   u'repos': [{u'path': u'../../../Everything/x86_64/os',
                                               u'repoid': u'Fedora-Everything',
                                               u'type': u'fedora'},
                                              {u'path': u'../../x86_64/debug', u'type': u'debug',
                                             u'repoid': u'Fedora-debuginfo'}],
                                   u'variant': u'Fedora',
                                   u'kernel_options': None,
                                   u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                                u'type': u'kernel'},
                                               {u'path': u'images/pxeboot/initrd.img',
                                                u'type': u'initrd'}],
                                   u'arches': [],
                                   u'urls': [u'http://localhost:19998/F-17/GOLD/Fedora/x86_64/os/'],
                                   u'arch': u'x86_64',
                                   u'ks_meta': None}


        self.i386_f17_compose = {u'osmajor': u'Fedora17',
                                 u'name': u'Fedora-17',
                                 u'tree_build_time': u'1337720321.88',
                                 u'osminor': u'0',
                                 u'tags': [],
                                 u'kernel_options_post': None,
                                 u'repos': [{u'path': u'../../../Everything/i386/os',
                                             u'repoid': u'Fedora-Everything',
                                             u'type': u'fedora'},
                                            {u'path': u'../../i386/debug', u'type': u'debug',
                                             u'repoid': u'Fedora-debuginfo'}],
                                 u'variant': u'Fedora',
                                 u'kernel_options': None,
                                 u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                              u'type': u'kernel'},
                                             {u'path': u'images/pxeboot/initrd.img',
                                              u'type': u'initrd'}],
                                 u'arches': [],
                                 u'urls': [u'http://localhost:19998/F-17/GOLD/Fedora/i386/os/'],
                                 u'arch': u'i386',
                                 u'ks_meta': None}


        self.x86_64_f18 = {u'osmajor': u'Fedora18',
                           u'name': u'Fedora-18',
                           u'tree_build_time': u'1357761579.49',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [{u'path': u'../../../Everything/x86_64/os',
                                       u'repoid': u'Fedora-Everything',
                                       u'type': u'fedora'},
                                      {u'path': u'../debug', u'type': u'debug',
                                       u'repoid': u'Fedora-debuginfo'}],
                           u'variant': u'Fedora',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-18/GOLD/Fedora/x86_64/os/'],
                           u'arch': u'x86_64',
                           u'ks_meta': None}

        self.i386_f18 = {u'osmajor': u'Fedora18',
                         u'name': u'Fedora-18',
                         u'tree_build_time': u'1357759821.15',
                         u'osminor': u'0',
                         u'tags': [],
                         u'kernel_options_post': None,
                         u'repos': [{u'path': u'../../../Everything/i386/os',
                                     u'repoid': u'Fedora-Everything',
                                     u'type': u'fedora'},
                                    {u'path': u'../debug', u'type': u'debug',
                                     u'repoid': u'Fedora-debuginfo'}],
                         u'variant': u'Fedora',
                         u'kernel_options': None,
                         u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                      u'type': u'kernel'},
                                     {u'path': u'images/pxeboot/initrd.img',
                                      u'type': u'initrd'}],
                         u'arches': [],
                         u'urls': [u'http://localhost:19998/F-18/GOLD/Fedora/i386/os/'],
                         u'arch': u'i386',
                         u'ks_meta': None}


        self.x86_64_f18_compose = {u'osmajor': u'Fedora18',
                                   u'name': u'Fedora-18',
                                   u'tree_build_time': u'1357761579.49',
                                   u'osminor': u'0',
                                   u'tags': [],
                                   u'kernel_options_post': None,
                                   u'repos': [{u'path': u'../../../Everything/x86_64/os',
                                               u'repoid': u'Fedora-Everything',
                                               u'type': u'fedora'},
                                              {u'path': u'../../x86_64/debug', u'type': u'debug',
                                               u'repoid': u'Fedora-debuginfo'}],
                                   u'variant': u'Fedora',
                                   u'kernel_options': None,
                                   u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                                u'type': u'kernel'},
                                               {u'path': u'images/pxeboot/initrd.img',
                                                u'type': u'initrd'}],
                                   u'arches': [],
                                   u'urls': [u'http://localhost:19998/F-18/GOLD/Fedora/x86_64/os/'],
                                   u'arch': u'x86_64',
                                   u'ks_meta': None}


        self.i386_f18_compose = {u'osmajor': u'Fedora18',
                                 u'name': u'Fedora-18',
                                 u'tree_build_time': u'1357759821.15',
                                 u'osminor': u'0',
                                 u'tags': [],
                                 u'kernel_options_post': None,
                                 u'repos': [{u'path': u'../../../Everything/i386/os',
                                             u'repoid': u'Fedora-Everything',
                                             u'type': u'fedora'},
                                            {u'path': u'../../i386/debug', u'type': u'debug',
                                             u'repoid': u'Fedora-debuginfo'}],
                                 u'variant': u'Fedora',
                                 u'kernel_options': None,
                                 u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                              u'type': u'kernel'},
                                             {u'path': u'images/pxeboot/initrd.img',
                                              u'type': u'initrd'}],
                                 u'arches': [],
                                 u'urls': [u'http://localhost:19998/F-18/GOLD/Fedora/i386/os/'],
                                 u'arch': u'i386',
                                 u'ks_meta': None}

        self.x86_64_rhel6_naked =  {u'arch': u'x86_64',
                                    u'arches': [u'x86_64'],
                                    u'images': [{u'path': u'/RHEL-6-Server-RHEV/6.4/6.4.1.1/vmlinuz0',
                                                 u'type': u'kernel'},
                                                {u'path': u'/RHEL-6-Server-RHEV/6.4/6.4.1.1/initrd0.img',
                                                 u'type': u'initrd'}],
                                    u'kernel_options': None,
                                    u'kernel_options_post': None,
                                    u'ks_meta': None,
                                    u'name': u'RHEVH-6.4-20130318.1',
                                    u'osmajor': u'RHEVH6',
                                    u'osminor': u'4',
                                    u'repos': [],
                                    u'tags': [],
                                    u'tree_build_time': 1366007531.817827,
                                    u'urls': [u'http://localhost:19998/RHEL-6-Server-RHEV/6.4/6.4.1.1/'],
                                    u'variant': u'Server'}

    def _run_import(self, import_args):
        p = subprocess.Popen(import_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=dict(os.environ.items() + [('PYTHONUNBUFFERED', '1')]))
        return p

    def _import_trees(self, additional_import_args, import_args=None):
        if not import_args:
            import_args = copy(self.import_args)
        import_args.extend(additional_import_args)
        p = self._run_import(import_args)
        stdout, stderr = p.communicate()
        if p.returncode:
            raise TreeImportError(import_args, p.returncode, stderr)
        json_trees = stdout.split('\n')
        del json_trees[-1] # Empty string
        trees = [json.loads(t) for t in json_trees]
        return trees


    def test_invalid_arch(self):
        rhel7_trees = self._import_trees(['--arch', 'i386', '--arch', 'x86_64',
            '%sRHEL7/' % self.distro_url])
        self.assertEquals(len(rhel7_trees), 4)

        f18_trees = self._import_trees(['--arch', 'CISC', '--arch', 'x86_64',
            '%sF-18/GOLD/Fedora' % self.distro_url])
        self.assertEquals(len(f18_trees), 1)

        rhel6_trees = self._import_trees(['--arch', 'AVR', '--arch', 'x86_64',
            '%sRHEL6-Server/' % self.distro_url])
        self.assertEquals(len(rhel6_trees), 1)

        rhel5_trees = self._import_trees(['--arch', 'RISC', '--arch', 'x86_64',
            '%sRHEL5-Server/' % self.distro_url])
        self.assertEquals(len(rhel5_trees), 1)

    def test_rhel6_naked_import(self):
        trees = self._import_trees(['%sRHEL-6-Server-RHEV/6.4/6.4.1.1/' % \
            self.distro_url, "--name", "RHEVH-6.4-20130318.1", "--family", \
            "RHEVH", "--variant", "Server", "--version", "6.4", "--kernel", \
            "/RHEL-6-Server-RHEV/6.4/6.4.1.1/vmlinuz0", "--initrd", \
            "/RHEL-6-Server-RHEV/6.4/6.4.1.1/initrd0.img", "--arch", "x86_64"])
        self.assertEqual(len(trees), 1)
        tree = trees[0]
        # Naked imports return the current time
        tree['tree_build_time'] = 1366007531.817827
        self.assertEquals(tree, self.x86_64_rhel6_naked)

    def test_rhel4_tree_import_compose(self):
        trees = self._import_trees(['%sRHEL-4/U9/AS/' % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.i386_rhel4)

    def test_rhel5_tree_import_compose(self):
        trees = self._import_trees(['%sRHEL5-Server/' % self.distro_url])
        self.assertTrue(len(trees) == 2) # Expecting two trees
        for tree in trees:
            if tree['arch'] == u'i386':
                i386_tree = tree
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree
        self.assertEquals(i386_tree, self.i386_rhel5)
        self.assertEquals(x86_64_tree, self.x86_64_rhel5)

    def test_rhel6_tree_import_compose(self):
        trees = self._import_trees(['%sRHEL6-Server/' % self.distro_url])
        self.assertTrue(len(trees) == 2) # Expecting two trees
        for tree in trees:
            if tree['arch'] == u'i386':
                i386_tree = tree
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree
        self.assertEquals(i386_tree, self.i386_rhel6)
        self.assertEquals(x86_64_tree, self.x86_64_rhel6)

    def test_rhel5_tree_import_tree(self):
        trees = self._import_trees(['%sRHEL5-Server/i386/os/'
            % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.i386_rhel5['name'] = 'RedHatEnterpriseLinuxServer-5.9'
        self.assertEquals(tree, self.i386_rhel5)

    def test_rhel6_tree_import_tree(self):
        trees = self._import_trees(['%sRHEL6-Server/x86_64/os/'
            % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.x86_64_rhel6['name'] = 'RedHatEnterpriseLinux-6.0'
        self.assertEquals(tree, self.x86_64_rhel6)

    def test_rhel7_tree_import_compose(self):
        trees = self._import_trees(['%sRHEL7/'% self.distro_url])

        self.assertTrue(len(trees) == 6)
        for tree in trees:
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree
            if tree['arch'] == u's390x':
                s390x_tree = tree
            if tree['arch'] == u'ppc64':
                ppc64_tree = tree

        self.assertEquals(x86_64_tree, self.x86_64_rhel7_compose)
        self.assertEquals(s390x_tree, self.s390x_rhel7_compose)
        self.assertEquals(ppc64_tree, self.ppc64_rhel7_compose)


    def test_f17_tree_import_i386(self):

        trees = self._import_trees(['%sF-17/GOLD/Fedora/i386/os'
                                    % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.i386_f17)

    def test_f17_tree_import_x86_64(self):

        trees = self._import_trees(['%sF-17/GOLD/Fedora/x86_64/os'
                                    % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.x86_64_f17)

    def test_f17_tree_import_compose(self):

        trees = self._import_trees(['%sF-17/GOLD/Fedora/' % self.distro_url])
        self.assertTrue(len(trees) == 2) # Expecting two trees
        for tree in trees:
            if tree['arch'] == u'i386':
                i386_tree = tree
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree

        self.assertEquals(i386_tree, self.i386_f17_compose)
        self.assertEquals(x86_64_tree, self.x86_64_f17_compose)


    def test_f18_tree_import_i386(self):

        trees = self._import_trees(['%sF-18/GOLD/Fedora/i386/os'
                                    % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.i386_f18)

    def test_f18_tree_import_x86_64(self):

        trees = self._import_trees(['%sF-18/GOLD/Fedora/x86_64/os'
                                    % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.x86_64_f18)

    def test_f18_tree_import_compose(self):

        trees = self._import_trees(['%sF-18/GOLD/Fedora/' % self.distro_url])
        self.assertTrue(len(trees) == 2) # Expecting two trees
        for tree in trees:
            if tree['arch'] == u'i386':
                i386_tree = tree
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree

        self.assertEquals(i386_tree, self.i386_f18_compose)
        self.assertEquals(x86_64_tree, self.x86_64_f18_compose)


    def test_selective_compose_import(self):
        trees = self._import_trees(['--arch', 'i386',
            '%sRHEL6-Server/' % self.distro_url])
        self.assertTrue(len(trees) == 1)
        tree = trees.pop()
        self.assertEquals(tree, self.i386_rhel6)

    #https://bugzilla.redhat.com/show_bug.cgi?id=907242
    def test_cannot_import_osmajor_existing_alias(self):

        # really import, not dry run
        import_args = ['python',_command,'--json','--debug']

        trees = self._import_trees(['%sRHEL6-Server/' % self.distro_url], import_args=import_args)
        self.assertTrue(len(trees) == 2) # Expecting two trees

        # set an alias
        myalias = 'RHEL6'
        with session.begin():
            distro1 = OSMajor.by_name('RedHatEnterpriseLinux6')
            distro1.alias = myalias
            self.assert_(distro1.alias is myalias)

        # import the same tree with osmajor same as myalias
        # beaker-import constructs the osmajor from family name and version
        # so, we just supply RHEL (and the osmajor will be RHEL6)
        try:
            trees = self._import_trees(['--family','RHEL',
                                        '%sRHEL6-Server/' % self.distro_url],
                                       import_args=import_args)
            self.fail('Must fail or die')
        except TreeImportError as e:
            self.assert_('Cannot import distro as RHEL6: '
                         'it is configured as an alias for RedHatEnterpriseLinux6' in
                         e.stderr_output, e.stderr_output)
