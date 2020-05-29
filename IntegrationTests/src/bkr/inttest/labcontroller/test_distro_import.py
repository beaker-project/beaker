
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import os
import subprocess
import json
import pkg_resources
import urlparse
from copy import copy, deepcopy
from bkr.inttest import Process
from bkr.inttest.labcontroller import LabControllerTestCase
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

class DistroImportTest(LabControllerTestCase):

    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.distro_server = Process('http_server.py', [sys.executable,
                    pkg_resources.resource_filename('bkr.inttest', 'http_server.py'),
                    '--base',  _compose_test_dir],
                listen_port=19998)
        cls.distro_server.start()
        cls.distro_url = u'http://localhost:19998/'

    @classmethod
    def tearDownClass(cls):
        cls.distro_server.stop()

    def setUp(self):
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

        self.x86_64_rhel66_server_nosap = {
            u'name': u'RHEL-6.6-20140731.1',
            u'osmajor': u'RedHatEnterpriseLinux6',
            u'osminor': u'6',
            u'variant': u'Server',
            u'tree_build_time' : u'1411608781',
            u'tags': [u'Beta-1.1'],
            u'repos': [
                {u'path': u'Server', u'type': u'variant', u'repoid': u'Server'},
                {u'path': u'HighAvailability', u'type': u'addon', u'repoid': u'HighAvailability'},
                {u'path': u'LoadBalancer', u'type': u'addon', u'repoid': u'LoadBalancer'},
                {u'path': u'ResilientStorage', u'type': u'addon', u'repoid': u'ResilientStorage'},
                {u'path': u'ScalableFileSystem', u'type': u'addon', u'repoid': u'ScalableFileSystem'},
                {u'path': u'../../../Server/optional/x86_64/os', u'type': u'optional', u'repoid': u'Server-optional'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arch': u'x86_64',
            u'arches': [],
            u'urls': [u'http://localhost:19998/RHEL-6.6-incomplete/Server/x86_64/os/'],
            u'ks_meta': None,
            u'kernel_options': None,
            u'kernel_options_post': None,
        }

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

        # Anything that was rolled on or before 20130606 should be considred legacy
        # The last release with this legacy style .treeinfo was Alpha-3
        self.x86_64_rhel7_alpha3_compose = {u'arch': u'x86_64',
                                    u'arches': [],
                                    u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                                                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
                                    u'kernel_options': None,
                                    u'kernel_options_post': None,
                                    u'ks_meta': None,
                                    u'name': u'RHEL-7.0-20120711.2',
                                    u'osmajor': u'RedHatEnterpriseLinux7',
                                    u'osminor': u'0',
                                    u'repos': [{u'path': u'', u'repoid': u'distro', u'type': u'distro'},
                                               {u'path': u'addons/ScalableFileSystem',
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
                                    u'urls': [u'http://localhost:19998/RHEL7Alpha3/Workstation/x86_64/os/',
                                              u'nfs://fake.example.com:/nfes/RHEL7Alpha3/Workstation/x86_64/os/',
                                              u'nfs+iso://fake.example.com:/nfes/RHEL7Alpha3/Workstation/x86_64/isometric/'],
                                    u'variant': u'Workstation'}

        self.s390x_rhel7_alpha3_compose= {u'arch': u's390x',
                                   u'arches': [],
                                   u'images': [{u'path': u'images/kernel.img', u'type': u'kernel'},
                                               {u'path': u'images/initrd.img', u'type': u'initrd'}],
                                   u'kernel_options': None,
                                   u'kernel_options_post': None,
                                   u'ks_meta': None,
                                   u'name': u'RHEL-7.0-20120711.2',
                                   u'osmajor': u'RedHatEnterpriseLinux7',
                                   u'osminor': u'0',
                                   u'repos': [{u'path': u'', u'repoid': u'distro', u'type': u'distro'},
                                              {u'path': u'../../../Server-optional/s390x/os',
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
                                   u'urls': [u'http://localhost:19998/RHEL7Alpha3/Server/s390x/os/',
                                             u'nfs://fake.example.com:/nfes/RHEL7Alpha3/Server/s390x/os/',
                                             u'nfs+iso://fake.example.com:/nfes/RHEL7Alpha3/Server/s390x/isobar/'],
                                   u'variant': u'Server'}

        self.ppc64_rhel7_alpha3_compose = { u'arch': u'ppc64',
                                     u'arches': [],
                                     u'images': [{u'path': u'ppc/ppc64/vmlinuz', u'type': u'kernel'},
                                                 {u'path': u'ppc/ppc64/initrd.img', u'type': u'initrd'}],
                                     u'kernel_options': None,
                                     u'kernel_options_post': None,
                                     u'ks_meta': None,
                                     u'name': u'RHEL-7.0-20120711.2',
                                     u'osmajor': u'RedHatEnterpriseLinux7',
                                     u'osminor': u'0',
                                     u'repos': [{u'path': u'', u'repoid': u'distro', u'type': u'distro'},
                                                {u'path': u'../../../Server-optional/ppc64/os',
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
                                     u'urls': [u'http://localhost:19998/RHEL7Alpha3/Server/ppc64/os/',
                                               u'nfs://fake.example.com:/nfes/RHEL7Alpha3/Server/ppc64/os/',
                                               u'nfs+iso://fake.example.com:/nfes/RHEL7Alpha3/Server/ppc64/isore/'],
                                     u'variant': u'Server'}

        self.x86_64_rhel7_client_compose = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'../../../Client-optional/x86_64/os',
                        u'repoid': u'Client-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../Client-optional/x86_64/debug/tree',
                        u'repoid': u'Client-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../Client/x86_64/os',
                        u'repoid': u'Client',
                        u'type': u'variant'},
                       {u'path': u'../../../Client/x86_64/debug/tree',
                        u'repoid': u'Client-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519626',
            u'urls': [u'http://localhost:19998/RHEL7/Client/x86_64/os/'],
            u'variant': u'Client'}

        self.ppc64_rhel7_server_compose = {
            u'arch': u'ppc64',
            u'arches': [],
            u'images': [{u'path': u'ppc/ppc64/vmlinuz', u'type': u'kernel'},
                        {u'path': u'ppc/ppc64/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'../../../Server-optional/ppc64/os',
                        u'repoid': u'Server-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../Server-optional/ppc64/debug/tree',
                        u'repoid': u'Server-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../Server/ppc64/os',
                        u'repoid': u'Server',
                        u'type': u'variant'},
                       {u'path': u'../../../Server/ppc64/debug/tree',
                        u'repoid': u'Server-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519647',
            u'urls': [u'http://localhost:19998/RHEL7/Server/ppc64/os/'],
            u'variant': u'Server'}

        self.s390x_rhel7_server_compose = {
            u'arch': u's390x',
            u'arches': [],
            u'images': [{u'path': u'images/kernel.img', u'type': u'kernel'},
                        {u'path': u'images/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'../../../Server-optional/s390x/os',
                        u'repoid': u'Server-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../Server-optional/s390x/debug/tree',
                        u'repoid': u'Server-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../Server/s390x/os',
                        u'repoid': u'Server',
                        u'type': u'variant'},
                       {u'path': u'../../../Server/s390x/debug/tree',
                        u'repoid': u'Server-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519659',
            u'urls': [u'http://localhost:19998/RHEL7/Server/s390x/os/'],
            u'variant': u'Server'}

        self.x86_64_rhel7_computenode_compose = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'../../../ComputeNode-optional/x86_64/os',
                        u'repoid': u'ComputeNode-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../ComputeNode-optional/x86_64/debug/tree',
                        u'repoid': u'ComputeNode-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../ComputeNode/x86_64/os',
                        u'repoid': u'ComputeNode',
                        u'type': u'variant'},
                       {u'path': u'../../../ComputeNode/x86_64/debug/tree',
                        u'repoid': u'ComputeNode-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519636',
            u'urls': [u'http://localhost:19998/RHEL7/ComputeNode/x86_64/os/'],
            u'variant': u'ComputeNode'}

        self.x86_64_rhel7_workstation_compose = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'../../../Workstation-optional/x86_64/os',
                        u'repoid': u'Workstation-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../Workstation-optional/x86_64/debug/tree',
                        u'repoid': u'Workstation-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../Workstation/x86_64/os',
                        u'repoid': u'Workstation',
                        u'type': u'variant'},
                       {u'path': u'../../../Workstation/x86_64/debug/tree',
                        u'repoid': u'Workstation-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519674',
            u'urls': [u'http://localhost:19998/RHEL7/Workstation/x86_64/os/'],
            u'variant': u'Workstation'}

        self.x86_64_rhel7_server_compose = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-7.0-20130930.n.0',
            u'osmajor': u'RedHatEnterpriseLinux7',
            u'osminor': u'0',
            u'repos': [{u'path': u'addons/HighAvailability',
                        u'repoid': u'HighAvailability',
                        u'type': u'addon'},
                       {u'path': u'addons/LoadBalancer',
                        u'repoid': u'LoadBalancer',
                        u'type': u'addon'},
                       {u'path': u'addons/ResilientStorage',
                        u'repoid': u'ResilientStorage',
                        u'type': u'addon'},
                       {u'path': u'../../../Server-optional/x86_64/os',
                        u'repoid': u'Server-optional',
                        u'type': u'optional'},
                       {u'path': u'../../../Server-optional/x86_64/debug/tree',
                        u'repoid': u'Server-optional-debuginfo',
                        u'type': u'debug'},
                       {u'path': u'../../../Server/x86_64/os',
                        u'repoid': u'Server',
                        u'type': u'variant'},
                       {u'path': u'../../../Server/x86_64/debug/tree',
                        u'repoid': u'Server-debuginfo',
                        u'type': u'debug'}],
            u'tags': [],
            u'tree_build_time': u'1380519663',
            u'urls': [u'http://localhost:19998/RHEL7/Server/x86_64/os/'],
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
                         u'urls': [u'http://localhost:19998/F-18/GOLD/Fedora/i386/os/',
                                   u'nfs://fake.example.com:/nfs/F-18/GOLD/Fedora/i386/os/',
                                   u'nfs+iso://fake.example.com:/nfs/F-18/GOLD/Fedora/i386/iso/'],
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

        self.i386_fedora_rawhide = {u'osmajor': u'Fedorarawhide',
                                    u'name': u'Fedora-rawhide-20130905',
                                    u'tree_build_time': u'1378389545.99',
                                    u'osminor': u'0',
                                    u'tags': [],
                                    u'kernel_options_post': None,
                                    u'repos': [{u'path': u'.', u'type': u'variant',
                                                u'repoid': u'Fedora'},
                                               {u'path': u'../../i386/debug', u'type': u'debug',
                                                u'repoid': u'Fedora-debuginfo'}],
                                    u'variant': u'Fedora',
                                    u'kernel_options': None,
                                    u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                                 u'type': u'kernel'},
                                                {u'path': u'images/pxeboot/initrd.img',
                                                 u'type': u'initrd'}],
                                    u'arches': [],
                                    u'urls': [u'http://localhost:19998/Fedora-rawhide/i386/os/'],
                                    u'arch': u'i386',
                                    u'ks_meta': None}

        self.x86_64_fedora_rawhide = {u'osmajor': u'Fedorarawhide',
                                    u'name': u'Fedora-rawhide-20130905',
                                    u'tree_build_time': u'1378389431.7',
                                    u'osminor': u'0',
                                    u'tags': [],
                                    u'kernel_options_post': None,
                                    u'repos': [{u'path': u'.', u'type': u'variant',
                                                u'repoid': u'Fedora'},
                                               {u'path': u'../../x86_64/debug', u'type': u'debug',
                                                u'repoid': u'Fedora-debuginfo'}],
                                    u'variant': u'Fedora',
                                    u'kernel_options': None,
                                    u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                                 u'type': u'kernel'},
                                                {u'path': u'images/pxeboot/initrd.img',
                                                 u'type': u'initrd'}],
                                    u'arches': [],
                                    u'urls': [u'http://localhost:19998/Fedora-rawhide/x86_64/os/'],
                                    u'arch': u'x86_64',
                                    u'ks_meta': None}

        self.armhfp_fedora_rawhide = {u'osmajor': u'Fedorarawhide',
                                      u'name': u'Fedora-rawhide-20130905',
                                      u'tree_build_time': u'1378390877.19',
                                      u'osminor': u'0',
                                      u'tags': [],
                                      u'kernel_options_post': None,
                                      u'repos': [{u'path': u'.', u'type': u'variant',
                                                u'repoid': u'Fedora'},
                                                 {u'path': u'../../armhfp/debug', u'type': u'debug',
                                                  u'repoid': u'Fedora-debuginfo'}],
                                      u'variant': u'Fedora',
                                    u'kernel_options': None,
                                      u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                                   u'type': u'kernel'},
                                                  {u'path': u'images/pxeboot/initrd.img',
                                                   u'type': u'initrd'},
                                                  {u'path': u'images/pxeboot/uImage',
                                                   u'type': u'uimage'},
                                                  {u'path': u'images/pxeboot/uInitrd',
                                                   u'type': u'uinitrd'},],
                                      u'arches': [
                                                  ],
                                      u'arches': [],
                                      u'urls': [u'http://localhost:19998/Fedora-rawhide/armhfp/os/'],
                                      u'arch': u'armhfp',
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

        self.x86_64_centos5 = {
            u'osmajor': u'CentOS5',
            u'osminor': u'10',
            u'name': u'CentOS-5.10',
            u'variant': u'',
            u'tree_build_time': u'1381776735.2',
            u'tags': [],
            u'repos': [
                {u'path': u'.', u'repoid': u'distro', u'type': u'distro'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/centos/5.10/os/x86_64/'],
            u'arch': u'x86_64',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }
        self.i386_centos5 = {
            u'osmajor': u'CentOS5',
            u'osminor': u'10',
            u'name': u'CentOS-5.10',
            u'variant': u'',
            u'tree_build_time': u'1381777520.0',
            u'tags': [],
            u'repos': [
                {u'path': u'.', u'repoid': u'distro', u'type': u'distro'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/centos/5.10/os/i386/'],
            u'arch': u'i386',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }

        self.x86_64_centos6 = {
            u'osmajor': u'CentOS6',
            u'osminor': u'5',
            u'name': u'CentOS-6.5',
            u'variant': u'',
            u'tree_build_time': u'1385726532.68',
            u'tags': [],
            u'repos': [
                {u'path': u'.', u'repoid': u'distro', u'type': u'distro'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/centos/6.5/os/x86_64/'],
            u'arch': u'x86_64',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }
        self.i386_centos6 = {
            u'osmajor': u'CentOS6',
            u'osminor': u'5',
            u'name': u'CentOS-6.5',
            u'variant': u'',
            u'tree_build_time': u'1385726461.69',
            u'tags': [],
            u'repos': [
                {u'path': u'.', u'repoid': u'distro', u'type': u'distro'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/centos/6.5/os/i386/'],
            u'arch': u'i386',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }

        self.x86_64_centos7 = {
            u'osmajor': u'CentOS7',
            u'osminor': u'0',
            u'name': u'CentOS-7',
            u'variant': u'',
            u'tree_build_time': u'1404489568.06',
            u'tags': [],
            u'repos': [
                {u'path': u'.', u'repoid': u'distro', u'type': u'distro'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/centos/7.0.1406/os/x86_64/'],
            u'arch': u'x86_64',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }

        self.rhs2 = {
            u'osmajor': u'RedHatStorage2',
            u'osminor': u'0',
            u'name': u'RHS-2.0-20120621.2',
            u'variant': u'RHS',
            u'tree_build_time': u'1340281615.186246',
            u'tags': [],
            u'repos': [
                {u'path': u'RHS', u'repoid': u'RHS', u'type': u'variant'},
                {u'path': u'../debug', u'repoid': u'debuginfo', u'type': u'debug'},
            ],
            u'images': [
                {u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'},
            ],
            u'arches': [],
            u'urls': [u'http://localhost:19998/RHS-2.0/x86_64/os/'],
            u'arch': u'x86_64',
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
        }

        self.x86_64_f21 = {u'osmajor': u'Fedora-Server21',
                           u'name': u'Fedora-Server-21',
                           u'tree_build_time': u'1417653911.68',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [
                               {u'path': u'.',
                                u'type': u'variant',
                                u'repoid': u'Fedora'},
                               {u'path': u'../../../Everything/x86_64/os',
                                u'repoid': u'Fedora-Everything',
                                u'type': u'fedora'},
                               {u'path': u'../../x86_64/debug', u'type': u'debug',
                                u'repoid': u'Server-debuginfo'}],
                           u'variant': u'Server',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-21/Server/x86_64/os/'],
                           u'arch': u'x86_64',
                           u'ks_meta': None}

        self.i386_f21 = {u'osmajor': u'Fedora-Server21',
                         u'name': u'Fedora-Server-21',
                         u'tree_build_time': u'1417650931.44',
                         u'osminor': u'0',
                         u'tags': [],
                         u'kernel_options_post': None,
                         u'repos': [
                             {u'path': u'.',
                              u'type': u'variant',
                              u'repoid': u'Fedora'},
                             {u'path': u'../../../Everything/i386/os',
                              u'repoid': u'Fedora-Everything',
                              u'type': u'fedora'},
                             {u'path': u'../../i386/debug', u'type': u'debug',
                              u'repoid': u'Server-debuginfo'}],
                         u'variant': u'Server',
                         u'kernel_options': None,
                         u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                      u'type': u'kernel'},
                                     {u'path': u'images/pxeboot/initrd.img',
                                      u'type': u'initrd'}],
                         u'arches': [],
                         u'urls': [u'http://localhost:19998/F-21/Server/i386/os/'],
                         u'arch': u'i386',
                         u'ks_meta': None}

        self.armhfp_f21 = {u'osmajor': u'Fedora-Server21',
                           u'name': u'Fedora-Server-21',
                           u'tree_build_time': u'1417645512.96',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [
                               {u'path': u'.',
                                u'type': u'variant',
                                u'repoid': u'Fedora'},
                               {u'path': u'../../../Everything/armhfp/os',
                                u'repoid': u'Fedora-Everything',
                                u'type': u'fedora'},
                               {u'path': u'../../armhfp/debug',
                                u'type': u'debug',
                                u'repoid': u'Server-debuginfo'}],
                           u'variant': u'Server',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'},
                                       {u'path': u'images/pxeboot/uImage',
                                        u'type': u'uimage'},
                                       {u'path': u'images/pxeboot/uInitrd',
                                        u'type': u'uinitrd'},
                                       {u'path': u'images/pxeboot/vmlinuz-lpae',
                                        u'type': u'kernel',
                                        u'kernel_type': u'lpae'},
                                       {u'path': u'images/pxeboot/uImage-lpae',
                                        u'type': u'uimage',
                                        u'kernel_type': u'lpae'},
                                       {u'path': u'images/pxeboot/initrd-lpae.img',
                                        u'type': u'initrd',
                                        u'kernel_type': u'lpae'},
                                       {u'path': u'images/pxeboot/uInitrd-lpae',
                                        u'type': u'uinitrd',
                                        u'kernel_type': u'lpae'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-21/Server/armhfp/os/'],
                           u'arch': u'armhfp',
                           u'ks_meta': None}

        self.x86_64_f25 = {u'osmajor': u'Fedora25',
                           u'name': u'Fedora-25',
                           u'tree_build_time': u'1479239952',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [
                               {u'path': u'.',
                                u'type': u'variant',
                                u'repoid': u'Fedora'},
                               {u'path': u'../../../Everything/x86_64/os',
                                u'repoid': u'Fedora-Everything',
                                u'type': u'fedora'},
                               {u'path': u'../debug', u'type': u'debug',
                                u'repoid': u'Fedora-debuginfo'}],
                           u'variant': u'Server',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-25/Server/x86_64/os/'],
                           u'arch': u'x86_64',
                           u'ks_meta': None}

        self.i386_f25 = {u'osmajor': u'Fedora25',
                         u'name': u'Fedora-25',
                         u'tree_build_time': u'1479239942',
                         u'osminor': u'0',
                         u'tags': [],
                         u'kernel_options_post': None,
                         u'repos': [
                             {u'path': u'.',
                              u'type': u'variant',
                              u'repoid': u'Fedora'},
                             {u'path': u'../../../Everything/i386/os',
                              u'repoid': u'Fedora-Everything',
                              u'type': u'fedora'},
                             {u'path': u'../debug', u'type': u'debug',
                              u'repoid': u'Fedora-debuginfo'}],
                         u'variant': u'Server',
                         u'kernel_options': None,
                         u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                      u'type': u'kernel'},
                                     {u'path': u'images/pxeboot/initrd.img',
                                      u'type': u'initrd'}],
                         u'arches': [],
                         u'urls': [u'http://localhost:19998/F-25/Server/i386/os/'],
                         u'arch': u'i386',
                         u'ks_meta': None}

        self.armhfp_f25 = {u'osmajor': u'Fedora25',
                           u'name': u'Fedora-25',
                           u'tree_build_time': u'1479239938',
                           u'osminor': u'0',
                           u'tags': [],
                           u'kernel_options_post': None,
                           u'repos': [
                               {u'path': u'.',
                                u'type': u'variant',
                                u'repoid': u'Fedora'},
                               {u'path': u'../../../Everything/armhfp/os',
                                u'repoid': u'Fedora-Everything',
                                u'type': u'fedora'},
                               {u'path': u'../debug',
                                u'type': u'debug',
                                u'repoid': u'Fedora-debuginfo'}],
                           u'variant': u'Server',
                           u'kernel_options': None,
                           u'images': [{u'path': u'images/pxeboot/vmlinuz',
                                        u'type': u'kernel'},
                                       {u'path': u'images/pxeboot/initrd.img',
                                        u'type': u'initrd'}],
                           u'arches': [],
                           u'urls': [u'http://localhost:19998/F-25/Server/armhfp/os/'],
                           u'arch': u'armhfp',
                           u'ks_meta': None}

        self.x86_64_rhel8 = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-8.0-20180531.2',
            u'osmajor': u'RedHatEnterpriseLinux8',
            u'osminor': u'0',
            u'repos': [
                {u'path': u'../../../BaseOS/x86_64/os',
                 u'repoid': u'BaseOS',
                 u'type': u'variant'},
                {u'path': u'../../../BaseOS/x86_64/debug/tree',
                 u'repoid': u'BaseOS-debuginfo',
                 u'type': u'debug'},
                {u'path': u'../../../../8.0-AppStream-Alpha/AppStream/x86_64/os',
                 u'repoid': u'AppStream',
                 u'type': u'variant'},
                {u'path': u'../../../../8.0-AppStream-Alpha/AppStream/x86_64/debug/tree',
                 u'repoid': u'AppStream-debuginfo',
                 u'type': u'debug'},
            ],
            u'tags': [u'Alpha-1.2'],
            u'tree_build_time': u'1523757763',
            u'urls': [u'http://localhost:19998/RHEL8Alpha/RHT/8.0-Alpha/BaseOS/x86_64/os/'],
            u'variant': u'BaseOS',
        }

        self.x86_64_rhel8_unified_partner_compose = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-8.0-20180531.2',
            u'osmajor': u'RedHatEnterpriseLinux8',
            u'osminor': u'0',
            u'repos': [
                {u'path': u'../../../AppStream/x86_64/os',
                 u'repoid': u'AppStream',
                 u'type': u'variant'},
                {u'path': u'../../../AppStream/x86_64/debug/tree',
                 u'repoid': u'AppStream-debuginfo',
                 u'type': u'debug'},
                {u'path': u'../../../BaseOS/x86_64/os',
                 u'repoid': u'BaseOS',
                 u'type': u'variant'},
                {u'path': u'../../../BaseOS/x86_64/debug/tree',
                 u'repoid': u'BaseOS-debuginfo',
                 u'type': u'debug'},
            ],
            u'tags': [u'Alpha-1.2'],
            u'tree_build_time': u'1523757763',
            u'urls': [u'http://localhost:19998/RHEL8Alpha/Unified/RHEL-8.0-20180531.2/compose/BaseOS/x86_64/os/'],
            u'variant': u'BaseOS',
        }

        self.x86_64_rhel8_partner = {
            u'arch': u'x86_64',
            u'arches': [],
            u'images': [{u'path': u'images/pxeboot/vmlinuz', u'type': u'kernel'},
                        {u'path': u'images/pxeboot/initrd.img', u'type': u'initrd'}],
            u'kernel_options': None,
            u'kernel_options_post': None,
            u'ks_meta': None,
            u'name': u'RHEL-8.0-20180531.2',
            u'osmajor': u'RedHatEnterpriseLinux8',
            u'osminor': u'0',
            u'repos': [
                {u'path': u'../../../BaseOS/x86_64/os',
                 u'repoid': u'BaseOS',
                 u'type': u'variant'},
                {u'path': u'../../../BaseOS/x86_64/debug/tree',
                 u'repoid': u'BaseOS-debuginfo',
                 u'type': u'debug'},
                {u'path': u'../../../../../AppStream-8.0-20180531.0/compose/AppStream/x86_64/os',
                 u'repoid': u'AppStream',
                 u'type': u'variant'},
                {u'path': u'../../../../../AppStream-8.0-20180531.0/compose/AppStream/x86_64/debug/tree',
                 u'repoid': u'AppStream-debuginfo',
                 u'type': u'debug'},
            ],
            u'tags': [u'Alpha-1.2'],
            u'tree_build_time': u'1523757763',
            u'urls': [u'http://localhost:19998/RHEL8Alpha/Partners/RHEL-8.0-20180531.2/compose/BaseOS/x86_64/os/'],
            u'variant': u'BaseOS',
        }

        self.x86_64_rhvh43 = {
            u"arch": u"x86_64",
            u"arches": [],
            u"images": [
                {
                    u"path": u"images/pxeboot/vmlinuz",
                    u"type": u"kernel"
                },
                {
                    u"path": u"images/pxeboot/initrd.img",
                    u"type": u"initrd"
                }
            ],
            u"kernel_options": u" inst.stage2={}".format(urlparse.urljoin(
                self.distro_url, u'RHVH4/RHVH-4.3-20200323.0/compose/RHVH/x86_64/os')),
            u"kernel_options_post": None,
            u"ks_meta": u" autopart_type=thinp liveimg=Packages/redhat-virtualization-host-image-update-1.0.0-1.noarch.rpm ks_keyword=inst.ks",
            u"name": u"RHVH-4.3-20200323.0",
            u"osmajor": u"RHVH4",
            u"osminor": u"3",
            u"repos": [
                {
                    u"path": u"../../../RHVH/x86_64/os",
                    u"repoid": u"RHVH",
                    u"type": u"variant"
                },
                {
                    u"path": u"../../../RHVH/x86_64/debug/tree",
                    u"repoid": u"RHVH-debuginfo",
                    u"type": u"debug"
                }
            ],
            u"tags": [
                u"RC-20200323.0"
            ],
            u"tree_build_time": u"1584961599",
            u"urls": [
                u"{}".format(urlparse.urljoin(self.distro_url, u'RHVH4/RHVH-4.3-20200323.0/compose/RHVH/x86_64/os/'))
            ],
            u"variant": u"RHVH"
        }

    def _run_import(self, import_args):
        p = subprocess.Popen(import_args,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             env=dict(os.environ.items() + [('PYTHONUNBUFFERED', '1')]))
        stdout, stderr = p.communicate()
        if p.returncode:
            raise TreeImportError(import_args, p.returncode, stderr)
        json_trees = stdout.splitlines()
        trees = [json.loads(t) for t in json_trees]
        return trees, stderr

    def dry_run_import_trees(self, additional_import_args):
        trees, stderr = self._run_import(
                ['python', _command, '--debug', '--json', '--dry-run']
                + additional_import_args)
        print stderr
        # check logging is working correctly
        self.assertIn('Dry Run only', stderr)
        self.assertIn('Attempting to import: ', stderr)
        # return dumped JSON tree info
        return trees

    def import_trees(self, additional_import_args):
        trees, stderr = self._run_import(
                ['python', _command, '--debug', '--json']
                + additional_import_args)
        # check logging is working correctly
        self.assertIn('Attempting to import: ', stderr)
        # return dumped JSON tree info
        return trees

    def test_invalid_arch(self):
        rhel7_trees = self.dry_run_import_trees(['--arch', 'i386', '--arch', 'x86_64',
            '%sRHEL7Alpha3/' % self.distro_url])
        self.assertEquals(len(rhel7_trees), 4)

        f18_trees = self.dry_run_import_trees(['--arch', 'CISC', '--arch', 'x86_64',
            '%sF-18/GOLD/Fedora' % self.distro_url])
        self.assertEquals(len(f18_trees), 1)

        rhel6_trees = self.dry_run_import_trees(['--arch', 'AVR', '--arch', 'x86_64',
            '%sRHEL6-Server/' % self.distro_url])
        self.assertEquals(len(rhel6_trees), 1)

        rhel5_trees = self.dry_run_import_trees(['--arch', 'RISC', '--arch', 'x86_64',
            '%sRHEL5-Server/' % self.distro_url])
        self.assertEquals(len(rhel5_trees), 1)

    def test_rhel6_naked_import(self):
        trees = self.dry_run_import_trees(['%sRHEL-6-Server-RHEV/6.4/6.4.1.1/' % \
            self.distro_url, "--name", "RHEVH-6.4-20130318.1", "--family", \
            "RHEVH", "--variant", "Server", "--version", "6.4", "--kernel", \
            "/RHEL-6-Server-RHEV/6.4/6.4.1.1/vmlinuz0", "--initrd", \
            "/RHEL-6-Server-RHEV/6.4/6.4.1.1/initrd0.img", "--arch", "x86_64"])
        self.assertEqual(len(trees), 1)
        tree = trees[0]
        # Naked imports return the current time
        tree['tree_build_time'] = 1366007531.817827
        self.assertEquals(tree, self.x86_64_rhel6_naked)

    def test_rhel5_tree_import_compose(self):
        trees = self.dry_run_import_trees(['%sRHEL5-Server/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_rhel5, self.x86_64_rhel5])

    def test_rhel6_tree_import_compose(self):
        trees = self.dry_run_import_trees(['%sRHEL6-Server/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_rhel6, self.x86_64_rhel6])

    def test_rhel5_tree_import_tree(self):
        trees = self.dry_run_import_trees(['%sRHEL5-Server/i386/os/'
            % self.distro_url])
        self.assertEquals(len(trees), 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.i386_rhel5['name'] = 'RedHatEnterpriseLinuxServer-5.9'
        self.assertEquals(tree, self.i386_rhel5)

    def test_rhel5_tree_import_tree_with_iso(self):
        trees = self.dry_run_import_trees(['%sRHEL5-Server/i386/os/'
            % self.distro_url, 'nfs://fake.example.com:/nfs/RHEL5-Server/i386/os/'])
        self.assertEquals(len(trees), 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.i386_rhel5['name'] = u'RedHatEnterpriseLinuxServer-5.9'
        self.i386_rhel5['urls']. \
            extend(['nfs://fake.example.com:/nfs/RHEL5-Server/i386/os/',
                'nfs+iso://fake.example.com:/nfs/RHEL5-Server/i386/iso/'])
        self.assertEquals(tree, self.i386_rhel5)

    def test_rhel6_import_tree_with_iso(self):
        trees = self.dry_run_import_trees(['%sRHEL6-Server/x86_64/os/'
            % self.distro_url,
            'nfs://invalid.example.com/RHEL6-Server/x86_64/os/'])
        self.assertEquals(len(trees), 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.x86_64_rhel6['name'] = u'RedHatEnterpriseLinux-6.0'
        self.x86_64_rhel6['urls'].extend(
            ['nfs://invalid.example.com/RHEL6-Server/x86_64/os/',
            'nfs+iso://invalid.example.com/RHEL6-Server/x86_64/iso/'])
        self.assertEquals(tree, self.x86_64_rhel6)

    def test_rhel6_tree_import_tree(self):
        trees = self.dry_run_import_trees(['%sRHEL6-Server/x86_64/os/'
            % self.distro_url])
        self.assertEquals(len(trees), 1)
        tree = trees.pop()
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.x86_64_rhel6['name'] = 'RedHatEnterpriseLinux-6.0'
        self.assertEquals(tree, self.x86_64_rhel6)

    def test_rhel7_tree_import_compose(self):
        trees = self.dry_run_import_trees(['%sRHEL7/'% self.distro_url])
        self.assertTrue(len(trees) == 6)
        self.assertItemsEqual(trees, [self.x86_64_rhel7_server_compose,
            self.x86_64_rhel7_client_compose, self.ppc64_rhel7_server_compose,
            self.s390x_rhel7_server_compose,
            self.x86_64_rhel7_computenode_compose,
            self.x86_64_rhel7_workstation_compose])

    def test_rhel7_alpha3_tree_import_compose_with_iso(self):
        trees = self.dry_run_import_trees(['%sRHEL7Alpha3/'% self.distro_url,
            'nfs://fake.example.com:/nfes/RHEL7Alpha3/'])

        self.assertEquals(len(trees), 6)
        for tree in trees:
            if tree['arch'] == u'x86_64':
                x86_64_tree = tree
            if tree['arch'] == u's390x':
                s390x_tree = tree
            if tree['arch'] == u'ppc64':
                ppc64_tree = tree

        self.assertEquals(x86_64_tree, self.x86_64_rhel7_alpha3_compose)
        self.assertEquals(s390x_tree, self.s390x_rhel7_alpha3_compose)
        self.assertEquals(ppc64_tree, self.ppc64_rhel7_alpha3_compose)

    def test_f17_tree_import_i386(self):

        trees = self.dry_run_import_trees(['%sF-17/GOLD/Fedora/i386/os'
                                    % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_f17])

    def test_f17_tree_import_x86_64(self):

        trees = self.dry_run_import_trees(['%sF-17/GOLD/Fedora/x86_64/os'
                                    % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_f17])

    def test_f17_tree_import_compose(self):

        trees = self.dry_run_import_trees(['%sF-17/GOLD/Fedora/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_f17_compose, self.x86_64_f17_compose])

    def test_f18_tree_import_i386_with_iso(self):

        trees = self.dry_run_import_trees(
            ['%sF-18/GOLD/Fedora/i386/os' % self.distro_url,
            'nfs://fake.example.com:/nfs/F-18/GOLD/Fedora/i386/os'])
        self.assertItemsEqual(trees, [self.i386_f18])

    def test_f18_tree_import_x86_64(self):

        trees = self.dry_run_import_trees(['%sF-18/GOLD/Fedora/x86_64/os'
            % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_f18])

    def test_f18_tree_import_compose(self):

        trees = self.dry_run_import_trees(['%sF-18/GOLD/Fedora/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_f18_compose, self.x86_64_f18_compose])

    def test_f21_server_tree_import_compose(self):

        trees = self.dry_run_import_trees(['%sF-21/Server/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_f21, self.x86_64_f21, self.armhfp_f21])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1412487
    def test_f25_tree_import_compose(self):
        trees = self.dry_run_import_trees(['%sF-25/' % self.distro_url])
        self.assertIn(self.i386_f25, trees)
        self.assertIn(self.x86_64_f25, trees)
        self.assertIn(self.armhfp_f25, trees)
        # There will also be Cloud, Workstation, and Everything trees
        # which we are not asserting here.

    def _rawhide_treeinfo(self, compose_tree):
        # "derive" the expected treeinfo data from the
        # composeinfo data
        compose_tree['name'] = u'Fedora-rawhide'
        compose_tree['variant'] = u''
        for repo in compose_tree['repos']:
            if repo['type'] == 'debug':
                repo['path'] = u'../debug'

        return compose_tree

    def test_fedora_rawhide_tree_import_i386(self):

        trees = self.dry_run_import_trees(['%sFedora-rawhide/i386/os'
                                           % self.distro_url])
        expected_tree = self._rawhide_treeinfo(
            compose_tree = deepcopy(self.i386_fedora_rawhide))
        self.assertItemsEqual(trees, [expected_tree])

    def test_fedora_rawhide_tree_import_x86_64(self):

        trees = self.dry_run_import_trees(['%sFedora-rawhide/x86_64/os'
                                           % self.distro_url])
        expected_tree = self._rawhide_treeinfo(
            compose_tree = deepcopy(self.x86_64_fedora_rawhide))
        self.assertItemsEqual(trees, [expected_tree])

    def test_fedora_rawhide_tree_import_armhfp(self):

        trees = self.dry_run_import_trees(['%sFedora-rawhide/armhfp/os'
                                           % self.distro_url])
        expected_tree = self._rawhide_treeinfo(
            compose_tree = deepcopy(self.armhfp_fedora_rawhide))
        self.assertItemsEqual(trees, [expected_tree])

    def test_fedora_rawhide_import_compose(self):

        trees = self.dry_run_import_trees(['%sFedora-rawhide/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_fedora_rawhide,
                self.x86_64_fedora_rawhide, self.armhfp_fedora_rawhide])

    def test_centos5_tree_import_i386(self):
        trees = self.dry_run_import_trees(['%scentos/5.10/os/i386' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_centos5])

    def test_centos5_tree_import_x86_64(self):
        trees = self.dry_run_import_trees(['%scentos/5.10/os/x86_64' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_centos5])

    def test_centos6_tree_import_i386(self):
        trees = self.dry_run_import_trees(['%scentos/6.5/os/i386' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_centos6])

    def test_centos6_tree_import_x86_64(self):
        trees = self.dry_run_import_trees(['%scentos/6.5/os/x86_64' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_centos6])

    def test_centos7_tree_import_x86_64(self):
        trees = self.dry_run_import_trees(['%scentos/7.0.1406/os/x86_64' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_centos7])

    def test_rhs2_compose_import(self):
        trees = self.dry_run_import_trees(['%sRHS-2.0' % self.distro_url])
        self.assertItemsEqual(trees, [self.rhs2])

    def test_rhs2_tree_import(self):
        trees = self.dry_run_import_trees(['%sRHS-2.0/x86_64/os' % self.distro_url])
        # See https://bugzilla.redhat.com/show_bug.cgi?id=910243
        # The following is actually a bug, but current behaviour
        # if there is no 'name' in .treeinfo's [general] section
        self.rhs2['name'] = u'RedHatStorage-2.0'
        self.assertItemsEqual(trees, [self.rhs2])

    def test_selective_compose_import(self):
        trees = self.dry_run_import_trees(['--arch', 'i386',
            '%sRHEL6-Server/' % self.distro_url])
        self.assertItemsEqual(trees, [self.i386_rhel6])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1140995
    def test_incomplete_compose(self):
        # We are importing a compose that is only selectively synced. Only
        # x86_64 Server should be imported, and missing add-on repos (SAP and
        # SAPHANA) should be skipped.
        trees = self.dry_run_import_trees(['%sRHEL-6.6-incomplete' % self.distro_url,
                '--ignore-missing-tree-compose'])
        self.assertItemsEqual(trees, [self.x86_64_rhel66_server_nosap])

    # https://bugzilla.redhat.com/show_bug.cgi?id=1140999
    def test_tags_from_composeinfo(self):
        # At least some RHEL6.6 composes have a label in .composeinfo but not
        # .treeinfo (whether intentionally or not).
        trees = self.dry_run_import_trees(['%sRHEL-6.6-incomplete' % self.distro_url,
                '--ignore-missing-tree-compose'])
        self.assertEquals(trees[0]['tags'], [u'Beta-1.1'])

    #https://bugzilla.redhat.com/show_bug.cgi?id=907242
    def test_cannot_import_osmajor_existing_alias(self):
        trees = self.import_trees(['%sRHEL6-Server/' % self.distro_url])
        self.assertEquals(len(trees), 2) # Expecting two trees

        # set an alias
        myalias = u'RHEL6'
        with session.begin():
            distro1 = OSMajor.by_name(u'RedHatEnterpriseLinux6')
            distro1.alias = myalias
            self.assert_(distro1.alias is myalias)

        # import the same tree with osmajor same as myalias
        # beaker-import constructs the osmajor from family name and version
        # so, we just supply RHEL (and the osmajor will be RHEL6)
        try:
            trees = self.import_trees(['--family', u'RHEL',
                                        '%sRHEL6-Server/' % self.distro_url])
            self.fail('Must fail or die')
        except TreeImportError as e:
            self.assert_('Cannot import distro as RHEL6: '
                         'it is configured as an alias for RedHatEnterpriseLinux6' in
                         e.stderr_output, e.stderr_output)

    def test_rhel8_import(self):
        trees = self.dry_run_import_trees(['%sRHEL8Alpha/RHT/8.0-Alpha/' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_rhel8])

    def test_preserve_install_options(self):
        trees = self.dry_run_import_trees([
            '--preserve-install-options',
            '%sRHEL8Alpha/RHT/8.0-Alpha/' % self.distro_url])
        for key in (u'kernel_options', u'kernel_options_post', u'ks_meta'):
            del self.x86_64_rhel8[key]
        # Verify that we do not have any of our Install Option values in the dictionary
        self.assertItemsEqual(trees, [self.x86_64_rhel8])

    def test_preserve_install_options_with_install_opt_fail(self):
        # import the tree with --preserve-install-options and one of --kopt,
        # --kopts-post, or --ks-meta. This should fail.
        for opt_name, key_name in (
             ('--kopts', u'kernel_options'),
             ('--kopts-post', u'kernel_options_post'),
             ('--ks-meta', u'ks_meta')
        ):
            try:
                self.dry_run_import_trees([
                    '--preserve-install-options',
                    opt_name, 'a_kernel_option'
                    '%sRHEL8Alpha/RHT/8.0-Alpha/' % self.distro_url])
                self.fail('Must fail or die')
            except TreeImportError as e:
                self.assertIn('--preserve-install-options can not be used with any of: '
                              '--kopt, --kopts-post, or --ks-meta',
                              e.stderr_output, msg=e.stderr_output)

    def test_rhel8_unified_partner_import(self):
        trees = self.dry_run_import_trees(['%sRHEL8Alpha/Unified/RHEL-8.0-20180531.2/compose' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_rhel8_unified_partner_compose])

    def test_rhel8_partner_import(self):
        trees = self.dry_run_import_trees(['%sRHEL8Alpha/Partners/RHEL-8.0-20180531.2/compose' % self.distro_url])
        self.assertItemsEqual(trees, [self.x86_64_rhel8_partner])

    def test_rhvh43_import(self):
        trees = self.dry_run_import_trees(['{}'.format(urlparse.urljoin(self.distro_url,
                                                                        'RHVH4/RHVH-4.3-20200323.0/compose'))])
        self.assertItemsEqual(trees, [self.x86_64_rhvh43])
