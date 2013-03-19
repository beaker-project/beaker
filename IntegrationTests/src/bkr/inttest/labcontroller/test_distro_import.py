import os
import unittest
import subprocess
import json
import pkg_resources
from bkr.inttest import Process

_current_dir = os.path.dirname(__file__)
_compose_test_dir = pkg_resources.resource_filename('bkr.inttest.labcontroller', 'compose_layout')
_git_root_dir = os.path.join(_current_dir, '..', '..', '..', '..', '..')

if os.path.exists(os.path.join(_git_root_dir, '.git')):
    # Looks like we are in a git checkout
    _command = os.path.join(_git_root_dir, 'LabController/src/bkr/labcontroller/distro_import.py')
else:
    _command = '/usr/bin/beaker-import'


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
                                       {u'path': u'../optional/x86_64/debug',
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
                                     {u'path': u'../optional/i386/debug',
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


        # separate expected tree data are maintained for import from .treeinfo
        # and .composeinfo, since Fedora's composeingo has debuginfo information
        # but, .treeinfo doesn't. See the sample files in compose_layout/ for examples

        self.x86_64_f17 = {u'osmajor': u'Fedora17',
                           u'name': u'Fedora-17',
                           u'tree_build_time': u'1337720130.41',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [{u'path': u'../debug', u'type': u'debug',
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
                         u'repos': [{u'path': u'../debug', u'type': u'debug',
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
                                   u'repos': [{u'path': u'../../x86_64/debug', u'type': u'debug',
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
                                 u'repos': [{u'path': u'../../i386/debug', u'type': u'debug',
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
                           u'repos': [{u'path': u'../debug', u'type': u'debug',
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
                         u'repos': [{u'path': u'../debug', u'type': u'debug',
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
                                   u'repos': [{u'path': u'../../x86_64/debug', u'type': u'debug',
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
                                 u'repos': [{u'path': u'../../i386/debug', u'type': u'debug',
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



    def _run_import(self, import_args):
        p = subprocess.Popen(import_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=dict(os.environ.items() + [('PYTHONUNBUFFERED', '1')]))
        return p

    def _import_trees(self, import_args):
        self.import_args.extend(import_args)
        p = self._run_import(self.import_args)
        stdout, stderr = p.communicate()
        self.assertEquals(p.returncode, 0,
            'Returned nonzero, stderr: %s' % stderr)
        json_trees = stdout.split('\n')
        del json_trees[-1] # Empty string
        trees = [json.loads(t) for t in json_trees]
        return trees

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
