import sys, os
import glob
import xmlrpclib
import string
import ConfigParser
import getopt
from optparse import OptionParser
import urllib2
import urlgrabber
import urlgrabber.progress
import logging
import socket
import copy
from bkr.common.bexceptions import BX

def url_exists(url):
    try:
        urllib2.urlopen(url)
    except urllib2.URLError:
        return False
    except urllib2.HTTPError:
        return False
    except IOError, e:
        # errno 21 is you tried to retrieve a directory.  Thats ok. We just
        # want to ensure the path is valid so far.
        if e.errno == 21:
            pass
        else:
            raise
    return True

class SchedulerProxy(object):
    """Scheduler Proxy"""
    def __init__(self, options):
        self.add_distro_cmd = options.add_distro_cmd
        # addDistroCmd = '/var/lib/beaker/addDistro.sh'
        self.proxy = xmlrpclib.ServerProxy('http://localhost:8000',
                                           allow_none=True)

    def add_distro(self, profile):
        try:
            self.proxy.register_distro(profile['name'])
        except xmlrpclib.Fault, e:
            # This is a hack to work around a race condition in Distro.lazy_create.
            # Remove this hack when that method is fixed.
            if 'IntegrityError' in e.faultString:
                pass
            else:
                raise
        return self.proxy.add_distro(profile)

    def run_distro_test_job(self, profile):
        if self.is_add_distro_cmd:
            cmd = self._make_add_distro_cmd(profile)
            logging.debug(cmd)
            os.system(cmd)
        else:
            raise BX('%s is missing' % self.add_distro_cmd)

    def _make_add_distro_cmd(self, profile):
        #addDistro.sh "rel-eng" RHEL6.0-20090626.2 RedHatEnterpriseLinux6.0 x86_64 "Default"
        cmd = '%s "%s" %s %s %s "%s"' % (
            self.add_distro_cmd,
            ','.join(profile.get('tags',[])),
            profile.get('treename'),
            '%s.%s' % (
            profile.get('osmajor'),
            profile.get('osminor')),
            profile.get('arch'),
            profile.get('variant', ''))
        return cmd

    @property
    def is_add_distro_cmd(self):
        # Kick off jobs automatically
        if os.path.exists(self.add_distro_cmd):
            return True
        return False


class CobblerProxy(object):
    def __init__(self, options):
        from cobbler import utils
        self.proxy = xmlrpclib.ServerProxy(options.lab)
        #cobbler = xmlrpclib.ServerProxy('http://127.0.0.1/cobbler_api')
        self.token = self.proxy.login("", utils.get_shared_secret())
        self.settings = self.proxy.get_settings(self.token)

    def add_distro(self, name, options):
        return self.proxy.xapi_object_edit('distro',
                                             name,
                                             'add',
                                             options,
                                             self.token)

    def add_profile(self, name, options):
        return self.proxy.xapi_object_edit('profile',
                                             name,
                                             'add',
                                             options,
                                             self.token)


class Parser(object):
    """
    base class to use for processing .composeinfo and .treeinfo
    """
    url = None
    parser = None

    def parse(self, url):
        self.url = url
        try:
            f = urllib2.urlopen('%s/%s' % (self.url, self.infofile))
            self.parser = ConfigParser.ConfigParser()
            self.parser.readfp(f)
            f.close()
        except urllib2.URLError:
            return False
        except urllib2.HTTPError:
            return False
        except ConfigParser.MissingSectionHeaderError, e:
            raise BX('%s/%s is not parsable: %s' % (self.url,
                                                      self.infofile,
                                                      e))
        return True

    def get(self, section, key, default=None):
        if self.parser:
            try:
                default = self.parser.get(section, key)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
                if default is None:
                    raise
        return default

    def __repr__(self):
        return '%s/%s' % (self.url, self.infofile)


class Cparser(Parser):
    infofile = '.composeinfo'

class Tparser(Parser):
    infofile = '.treeinfo'

class Importer(object):
    def __init__(self, parser):
        self.parser = parser


class ComposeInfoBase(object):
    @classmethod
    def is_importer_for(cls, url):
        parser = Cparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r['section'], r['key'], '') == '':
                return False
        for e in cls.excluded:
            if parser.get(e['section'], e['key'], '') != '':
                return False
        return parser


class ComposeInfoLegacy(ComposeInfoBase, Importer):
    """
    [tree]
    arches = i386,x86_64,ia64,ppc64,s390,s390x
    name = RHEL4-U8
    """
    required = [dict(section='tree', key='name'),
               ]
    excluded = [dict(section='product', key='variants'),
               ]
    arches = ['i386', 'x86_64', 'ia64', 'ppc', 'ppc64', 's390', 's390x']
    os_dirs = ['os', 'tree']

    def get_arches(self):
        """ Return a list of arches
        """
        return filter(lambda x: url_exists(os.path.join(self.parser.url,x)) \
                      and x, [arch for arch in self.arches])

    def get_os_dir(self, arch):
        """ Return path to os directory
        """
        base_path = os.path.join(self.parser.url, arch)
        try:
            os_dir = filter(lambda x: url_exists(os.path.join(base_path, x)) \
                            and x, self.os_dirs)[0]
        except IndexError, e:
            raise BX('%s no os_dir found: %s' % (base_path, e))
        return os.path.join(arch, os_dir)

    def process(self, options):
        self.options = options
        for arch in self.get_arches():
            os_dir = self.get_os_dir(arch)
            ks_meta = dict()
            options = copy.deepcopy(self.options)
            if not options.name:
                options.name = self.parser.get('tree', 'name')
            if options.available_as:
                options.available_as = os.path.join(options.available_as,
                                                    os_dir)
            try:
                build = Build(os.path.join(self.parser.url, os_dir))
                build.process(options, ks_meta)
            except BX, err:
                logging.warn(err)


class ComposeInfo(ComposeInfoBase, Importer):
    """
[product]
family = RHEL
name = Red Hat Enterprise Linux
variants = Client,ComputeNode,Server,Workstation
version = 7.0

[variant-Client]
arches = x86_64
id = Client
name = Client
type = variant
uid = Client
variants = Client-optional

[variant-Client-optional]
arches = x86_64
id = optional
name = optional
parent = Client
type = optional
uid = Client-optional
variants = 

[variant-Client-optional.x86_64]
arch = x86_64
debuginfo = Client-optional/x86_64/debuginfo
os_dir = Client-optional/x86_64/os
packages = Client-optional/x86_64/os/Packages
parent = Client.x86_64
repository = Client-optional/x86_64/os
sources = Client-optional/source/SRPMS

[variant-Client.x86_64]
arch = x86_64
debuginfo = Client/x86_64/debuginfo
isos = Client/x86_64/iso
os_dir = Client/x86_64/os
packages = Client/x86_64/os/Packages
repository = Client/x86_64/os
source_isos = Client/source/iso
sources = Client/source/SRPMS

[variant-ComputeNode]
arches = x86_64
id = ComputeNode
name = Compute Node
type = variant
uid = ComputeNode
variants = ComputeNode-optional

[variant-ComputeNode-optional]
arches = x86_64
id = optional
name = optional
parent = ComputeNode
type = optional
uid = ComputeNode-optional
variants = 

[variant-ComputeNode-optional.x86_64]
arch = x86_64
debuginfo = ComputeNode-optional/x86_64/debuginfo
os_dir = ComputeNode-optional/x86_64/os
packages = ComputeNode-optional/x86_64/os/Packages
parent = ComputeNode.x86_64
repository = ComputeNode-optional/x86_64/os
sources = ComputeNode-optional/source/SRPMS

[variant-ComputeNode.x86_64]
arch = x86_64
debuginfo = ComputeNode/x86_64/debuginfo
isos = ComputeNode/x86_64/iso
os_dir = ComputeNode/x86_64/os
packages = ComputeNode/x86_64/os/Packages
repository = ComputeNode/x86_64/os
source_isos = ComputeNode/source/iso
sources = ComputeNode/source/SRPMS

[variant-Server]
arches = ppc64,s390x,x86_64
id = Server
name = Server
type = variant
uid = Server
variants = Server-HighAvailability,Server-LoadBalancer,Server-ResilientStorage,Server-ScalableFileSystem,Server-optional

[variant-Server-HighAvailability]
arches = x86_64
id = HighAvailability
name = High Availability
parent = Server
type = addon
uid = Server-HighAvailability
variants = 

[variant-Server-HighAvailability.x86_64]
arch = x86_64
debuginfo = Server/x86_64/debuginfo
os_dir = Server/x86_64/os
packages = Server/x86_64/os/addons/HighAvailability
parent = Server.x86_64
repository = Server/x86_64/os/addons/HighAvailability
sources = Server/source/SRPMS

[variant-Server-LoadBalancer]
arches = x86_64
id = LoadBalancer
name = Load Balancer
parent = Server
type = addon
uid = Server-LoadBalancer
variants = 

[variant-Server-LoadBalancer.x86_64]
arch = x86_64
debuginfo = Server/x86_64/debuginfo
os_dir = Server/x86_64/os
packages = Server/x86_64/os/addons/LoadBalancer
parent = Server.x86_64
repository = Server/x86_64/os/addons/LoadBalancer
sources = Server/source/SRPMS

[variant-Server-ResilientStorage]
arches = x86_64
id = ResilientStorage
name = Resilient Storage
parent = Server
type = addon
uid = Server-ResilientStorage
variants = 

[variant-Server-ResilientStorage.x86_64]
arch = x86_64
debuginfo = Server/x86_64/debuginfo
os_dir = Server/x86_64/os
packages = Server/x86_64/os/addons/ResilientStorage
parent = Server.x86_64
repository = Server/x86_64/os/addons/ResilientStorage
sources = Server/source/SRPMS

[variant-Server-ScalableFileSystem]
arches = x86_64
id = ScalableFileSystem
name = Scalable Filesystem Support
parent = Server
type = addon
uid = Server-ScalableFileSystem
variants = 

[variant-Server-ScalableFileSystem.x86_64]
arch = x86_64
debuginfo = Server/x86_64/debuginfo
os_dir = Server/x86_64/os
packages = Server/x86_64/os/addons/ScalableFileSystem
parent = Server.x86_64
repository = Server/x86_64/os/addons/ScalableFileSystem
sources = Server/source/SRPMS

[variant-Server-optional]
arches = ppc64,s390x,x86_64
id = optional
name = optional
parent = Server
type = optional
uid = Server-optional
variants = 

[variant-Server-optional.ppc64]
arch = ppc64
debuginfo = Server-optional/ppc64/debuginfo
os_dir = Server-optional/ppc64/os
packages = Server-optional/ppc64/os/Packages
parent = Server.ppc64
repository = Server-optional/ppc64/os
sources = Server-optional/source/SRPMS

[variant-Server-optional.s390x]
arch = s390x
debuginfo = Server-optional/s390x/debuginfo
os_dir = Server-optional/s390x/os
packages = Server-optional/s390x/os/Packages
parent = Server.s390x
repository = Server-optional/s390x/os
sources = Server-optional/source/SRPMS

[variant-Server-optional.x86_64]
arch = x86_64
debuginfo = Server-optional/x86_64/debuginfo
os_dir = Server-optional/x86_64/os
packages = Server-optional/x86_64/os/Packages
parent = Server.x86_64
repository = Server-optional/x86_64/os
sources = Server-optional/source/SRPMS

[variant-Server.ppc64]
arch = ppc64
debuginfo = Server/ppc64/debuginfo
isos = Server/ppc64/iso
os_dir = Server/ppc64/os
packages = Server/ppc64/os/Packages
repository = Server/ppc64/os
source_isos = Server/source/iso
sources = Server/source/SRPMS

[variant-Server.s390x]
arch = s390x
debuginfo = Server/s390x/debuginfo
isos = Server/s390x/iso
os_dir = Server/s390x/os
packages = Server/s390x/os/Packages
repository = Server/s390x/os
source_isos = Server/source/iso
sources = Server/source/SRPMS

[variant-Server.x86_64]
arch = x86_64
debuginfo = Server/x86_64/debuginfo
isos = Server/x86_64/iso
os_dir = Server/x86_64/os
packages = Server/x86_64/os/Packages
repository = Server/x86_64/os
source_isos = Server/source/iso
sources = Server/source/SRPMS

[variant-Workstation]
arches = x86_64
id = Workstation
name = Workstation
type = variant
uid = Workstation
variants = Workstation-ScalableFileSystem,Workstation-optional

[variant-Workstation-ScalableFileSystem]
arches = x86_64
id = ScalableFileSystem
name = Scalable Filesystem Support
parent = Workstation
type = addon
uid = Workstation-ScalableFileSystem
variants = 

[variant-Workstation-ScalableFileSystem.x86_64]
arch = x86_64
debuginfo = Workstation/x86_64/debuginfo
os_dir = Workstation/x86_64/os
packages = Workstation/x86_64/os/addons/ScalableFileSystem
parent = Workstation.x86_64
repository = Workstation/x86_64/os/addons/ScalableFileSystem
sources = Workstation/source/SRPMS

[variant-Workstation-optional]
arches = x86_64
id = optional
name = optional
parent = Workstation
type = optional
uid = Workstation-optional
variants = 

[variant-Workstation-optional.x86_64]
arch = x86_64
debuginfo = Workstation-optional/x86_64/debuginfo
os_dir = Workstation-optional/x86_64/os
packages = Workstation-optional/x86_64/os/Packages
parent = Workstation.x86_64
repository = Workstation-optional/x86_64/os
sources = Workstation-optional/source/SRPMS

[variant-Workstation.x86_64]
arch = x86_64
debuginfo = Workstation/x86_64/debuginfo
isos = Workstation/x86_64/iso
os_dir = Workstation/x86_64/os
packages = Workstation/x86_64/os/Packages
repository = Workstation/x86_64/os
source_isos = Workstation/source/iso
sources = Workstation/source/SRPMS

    """
    required = [dict(section='product', key='variants'),
               ]
    excluded = []

    def get_arches(self, variant):
        """ Return a list of arches for variant
        """
        return self.parser.get('variant-%s' %
                                          variant, 'arches').split(',')

    def get_variants(self):
        """ Return a list of variants
        """
        return self.parser.get('product', 'variants').split(',')

    def find_repos(self, repo_base, variant, arch, ks_meta):
        """ Find all variant repos
        """
        variants = self.parser.get('variant-%s' % (variant), 'variants', '')
        if variants:
            for sub_variant in variants.split(','):
                ks_meta = self.find_repos(repo_base, sub_variant,
                                          arch, ks_meta)

        # Skip addon variants from .composeinfo, we pick these up from 
        # .treeinfo
        if self.parser.get('variant-%s' % variant, 'type') == 'addon':
            return ks_meta

        repo = self.parser.get('variant-%s.%s' % (variant, arch), 
                               'repository', '')
        if repo:
            ks_meta['repos'].append(variant)
            ks_meta['repos_%s' % variant] = os.path.join(repo_base, repo)

        return ks_meta

    def find_debug(self, repo_base, variant, arch, ks_meta):
        """ Find all debug repos, including ones belonging to optional
        """
        variants = self.parser.get('variant-%s' % (variant), 'variants', '')
        if variants:
            for sub_variant in variants.split(','):
                ks_meta = self.find_debug(repo_base, sub_variant,
                                          arch, ks_meta)

        # Skip addon variants from .composeinfo, we pick these up from 
        # .treeinfo
        if self.parser.get('variant-%s' % variant, 'type') == 'addon':
            return ks_meta

        # Add debug to ks_meta['repos'] if not already there
        if 'debug' not in ks_meta['repos']:
            ks_meta['repos'].append('debug')
        # Initialize repos_debug array if needed
        if 'repos_debug' not in ks_meta:
            ks_meta['repos_debug'] = []
        
        repo = self.parser.get('variant-%s.%s' % (variant, arch), 
                               'debuginfo', '')
        if repo:
            variant = variant.replace('-','_')
            ks_meta['repos_debug'].append(variant)
            ks_meta['repos_debug_%s' % variant] = os.path.join(repo_base, repo)

        return ks_meta

    def process(self, options):
        self.options = options

        for variant in self.get_variants():
            for arch in self.get_arches(variant):
                os_dir = self.parser.get('variant-%s.%s' %
                                              (variant, arch), 'os_dir')
                options = copy.deepcopy(self.options)
                ks_meta = dict(repos=[])
                if not options.name:
                    options.name = self.parser.get('product', 'name')

                # If repo_available_as is defined then populate additional
                # repos
                if options.repo_available_as:
                    ks_meta = self.find_debug(options.repo_available_as,
                                              variant, arch, ks_meta)
                    ks_meta = self.find_repos(options.repo_available_as,
                                              variant, arch, ks_meta)
                    options.repo_available_as = os.path.join(options.repo_available_as, os_dir)
                if options.available_as:
                    options.available_as = os.path.join(options.available_as,
                                                        os_dir)
                try:
                    build = Build(os.path.join(self.parser.url, os_dir))
                    build.process(options, ks_meta)
                except BX, err:
                    logging.warn(err)


class TreeInfoBase(object):
    """
    Base class for TreeInfo methods
    """
    required = [dict(section='general', key='family'),
                dict(section='general', key='version'),
                dict(section='general', key='arch'),
               ]
    excluded = []

    def process(self, options, profile_ks_meta=dict()):
        self.options = options
        self.cobbler = CobblerProxy(options)
        self.scheduler = SchedulerProxy(options)
        self.kickbase = os.path.dirname(self.cobbler.settings.get('default_kickstart'))
        #self.kickbase = "/var/lib/cobbler/kickstarts"
        self.tree = dict()
        self.tree['kernel_options'] = ''
        if self.options.available_as:
            url = self.options.available_as
        else:
            url = self.parser.url
        self.tree['ks_meta'] = dict(tree=url)
        self.tree['breed'] = 'redhat'
        family  = self.parser.get('general', 'family').replace(" ","")
        version = self.parser.get('general', 'version').replace("-",".")
        self.tree['treename'] = self.options.name or \
                                   self.parser.get('general', 'name', 
                                   '%s-%s' % (family,version)
                                                    )
        self.tree['variant'] = self.parser.get('general','variant','')
        self.tree['arch'] = self.parser.get('general','arch')
        self.tree['tree_build_time'] = self.parser.get('general','timestamp',0.0)
        labels = self.parser.get('general', 'label','')
        self.tree['tags'] = list(set(self.options.tags).union(
                                    set(map(string.strip,
                                    labels and labels.split(',') or []))))
        self.tree['name'] = '%s-%s-%s' % (self.tree['treename'],
                                             self.tree['variant'],
                                             self.tree['arch'],
                                            )
        self.tree['osmajor'] = "%s%s" % (family, version.split('.')[0])
        if version.find('.') != -1:
            self.tree['osminor'] = version.split('.')[1]
        else:
            self.tree['osminor'] = '0'

        arches = self.parser.get('general', 'arches','')
        self.tree['arches'] = map(string.strip,
                                     arches and arches.split(',') or [])
        # if repo_availble_as is defined include addon repos
        if self.options.repo_available_as:
            profile_ks_meta = self.find_addon_repos(profile_ks_meta)
        self.tree['profile_ks_meta'] = profile_ks_meta

        # if root option is specified then look for stage2
        if self.options.root:
            self.tree['kernel_options'] = 'root=live:%s' % os.path.join(
                                         url,
                                         self.parser.get('stage2', 'mainimage')
                                                                       )

        logging.debug('tree: %s' % self.tree)
        try:
            self.add_to_cobbler()
            logging.info('%s added to cobbler.' % self.tree['name'])
        except (xmlrpclib.Fault, socket.error), e:
            raise BX('failed to add %s to cobbler: %s' % (self.tree['name'],e))
        try:
            self.add_to_beaker()
            logging.info('%s added to beaker.' % self.tree['name'])
        except (xmlrpclib.Fault, socket.error), e:
            raise BX('failed to add %s to beaker: %s' % (self.tree['name'],e))
        if self.options.run_jobs:
            logging.info('running jobs.')
            self.run_jobs()

    def find_addon_repos(self, ks_meta):
        """
        using info from .treeinfo find addon repos
        """
        try:
            # Initialize ks_meta['repos'] if needed
            if 'repos' not in ks_meta:
                ks_meta['repos'] = []
            ks_meta['repos'].append('addons')
            ks_meta['repos_addons'] = self.parser.get('variant-%s', 
                                    self.tree['variant'], 'addons').split(',')
            for addon in ks_meta['repos_addons']:
                ks_meta['repos_addons_%s' % addon] = os.path.join(
                                        self.options.repo_available_as,
                                        self.parser.get('addon-%s' % addon, 'repository')
                                                                 )
            return ks_meta
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            logging.debug('no addon repos for %s, %s' % (self.parser.url,e))
            return ks_meta

    def sync_images(self):
        """
        using info from .treeinfo pull down install images
        """
        kernel = self.get_kernel_path()
        initrd = self.get_initrd_path()
        directory = '%s/localmirror/%s' % (self.cobbler.settings['webdir'],
                                           self.tree['name'])
    
        kernel_url='%s/%s' % (self.parser.url, kernel)
        initrd_url='%s/%s' % (self.parser.url, initrd)
    
        if not os.path.exists(directory):
            logging.debug('make directories: %s' % directory)
            os.makedirs(directory)

        if self.options.quiet:
            prog_meter = None
        else:
            prog_meter = urlgrabber.progress.TextMeter()

        try:
            self.tree['kernel'] = urlgrabber.grabber.urlgrab(kernel_url,
                                           filename='%s/%s' % (directory,
                                                    os.path.basename(kernel_url)),
                                           progress_obj=prog_meter)
        except urlgrabber.grabber.URLGrabError, e:
            raise BX(e)
        try:
            self.tree['initrd'] = urlgrabber.grabber.urlgrab(initrd_url,
                                           filename='%s/%s' % (directory,
                                                    os.path.basename(initrd_url)),
                                           progress_obj=prog_meter)
        except urlgrabber.grabber.URLGrabError, e:
            raise BX(e)

    def add_to_cobbler(self):
        """
        Add distro/profile to cobbler
        """
        self.sync_images()
        if self.options.kickstart:
            if os.path.exists(self.options.kickstart):
                kickstart = self.options.kickstart
            else:
                raise BX('kickstart %s does not exist' % self.options.kickstart)
        else:
            kickstart = self.find_kickstart(
                                            self.tree['arch'],
                                            self.tree['osmajor'],
                                            self.tree['osminor']
                                           )
        distro_options = dict(name = self.tree['name'],
                              kernel = self.tree['kernel'],
                              kernel_options = self.tree['kernel_options'],
                              initrd = self.tree['initrd'],
                              arch = self.tree['arch'],
                              ks_meta = self.tree['ks_meta'],
                             )
        profile_options = dict(distro = self.tree['name'],
                               name = self.tree['name'],
                               kickstart = kickstart,
                               ks_meta = self.tree['profile_ks_meta'],
                               comment = 'ignore',
                              )
        self.cobbler.add_distro(self.tree['name'],
                                             distro_options)
        self.cobbler.add_profile(self.tree['name'],
                                     profile_options)

    def add_to_beaker(self):
        self.scheduler.add_distro(self.tree)

    def run_jobs(self):
        self.scheduler.run_distro_test_job(self.tree)

    def find_kickstart(self, arch, family, update):
        flavor = family.strip('0123456789')
        kickstarts = [
               "%s/%s/%s.%s.ks" % (self.kickbase, arch, family, update),
               "%s/%s/%s.ks" % (self.kickbase, arch, family),
               "%s/%s/%s.ks" % (self.kickbase, arch, flavor),
               "%s/%s.%s.ks" % (self.kickbase, family, update),
               "%s/%s.ks" % (self.kickbase, family),
               "%s/%s.ks" % (self.kickbase, flavor),
        ]
        for kickstart in kickstarts:
            if os.path.exists(kickstart):
                return kickstart
        return self.cobbler.settings.get('default_kickstart')


class TreeInfoLegacy(TreeInfoBase, Importer):
    """
    This version of .treeinfo importer has a workaround for missing
    images-$arch sections.
    """
    kernels = ['images/pxeboot/vmlinuz',
               'images/kernel.img',
               'ppc/ppc64/vmlinuz',
               'ppc/iSeries/vmlinux',
              ]
    initrds = ['images/pxeboot/initrd.img',
               'images/initrd.img',
               'ppc/ppc64/ramdisk.image.gz',
               'ppc/iSeries/ramdisk.image.gz',
              ]

    @classmethod
    def is_importer_for(cls, url):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r['section'], r['key'], '') == '':
                return False
        for e in cls.excluded:
            if parser.get(e['section'], e['key'], '') != '':
                return False
        if not parser.get('general', 'family').startswith("Red Hat Enterprise Linux"):
            return False
        if int(parser.get('general', 'version').split('.')[0]) > 6:
            return False
        return parser

    def get_kernel_path(self):
        try:
            return filter(lambda x: url_exists(os.path.join(self.parser.url,x)) \
                          and x, [kernel for kernel in self.kernels])[0]
        except IndexError, e:
            raise BX('%s no kernel found: %s' % (self.parser.url, e))

    def get_initrd_path(self):
        try:
            return filter(lambda x: url_exists(os.path.join(self.parser.url,x)) \
                          and x, [initrd for initrd in self.initrds])[0]
        except IndexError, e:
            raise BX('%s no kernel found: %s' % (self.parser.url, e))


class TreeInfoFedora(TreeInfoBase, Importer):
    """

    """
    @classmethod
    def is_importer_for(cls, url):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r['section'], r['key'], '') == '':
                return False
        for e in cls.excluded:
            if parser.get(e['section'], e['key'], '') != '':
                return False
        if not parser.get('general', 'family').startswith("Fedora"):
            return False
        return parser

    def get_kernel_path(self):
        return self.parser.get('images-%s' % self.tree['arch'].replace('ppc','ppc64'),'kernel')

    def get_initrd_path(self):
        return self.parser.get('images-%s' % self.tree['arch'].replace('ppc','ppc64'),'initrd')

    def find_addon_repos(self, ks_meta):
        """
        using info from known locations

        """

        # ppc64 arch uses ppc for the repos
        arch = self.tree['arch'].replace('ppc64','ppc')

        repo_paths = [('Fedora',
                       'variant',
                       '.'),
                     ]
        # Initialize ks_meta['repos'] if needed
        if 'repos' not in ks_meta:
            ks_meta['repos'] = []
        ks_meta['repos'].append('addons')
        ks_meta['repos_addons'] = []
        for repo in repo_paths:
            if url_exists(os.path.join(self.parser.url,repo[2],'repodata')):
                ks_meta['repos_addons'].append(repo[0])
                ks_meta['repos_addons_%s' % repo[0]] = os.path.join(
                                          self.options.repo_available_as,
                                                            repo[2])
        return ks_meta

class TreeInfoRhel(TreeInfoBase, Importer):
    """
[addon-HighAvailability]
id = HighAvailability
name = High Availability
repository = addons/HighAvailability
uid = Server-HighAvailability

[addon-LoadBalancer]
id = LoadBalancer
name = Load Balancer
repository = addons/LoadBalancer
uid = Server-LoadBalancer

[addon-ResilientStorage]
id = ResilientStorage
name = Resilient Storage
repository = addons/ResilientStorage
uid = Server-ResilientStorage

[addon-ScalableFileSystem]
id = ScalableFileSystem
name = Scalable Filesystem Support
repository = addons/ScalableFileSystem
uid = Server-ScalableFileSystem

[general]
addons = HighAvailability,LoadBalancer,ResilientStorage,ScalableFileSystem
arch = x86_64
family = Red Hat Enterprise Linux
version = 7.0
variant = Server
timestamp = 
name = RHEL-7.0-20120201.0
repository = 

[images-x86_64]
boot.iso = images/boot.iso
initrd = images/pxeboot/initrd.img
kernel = images/pxeboot/vmlinuz

[images-xen]
initrd = images/pxeboot/initrd.img
kernel = images/pxeboot/vmlinuz

    """
    @classmethod
    def is_importer_for(cls, url):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r['section'], r['key'], '') == '':
                return False
        for e in cls.excluded:
            if parser.get(e['section'], e['key'], '') != '':
                return False
        if parser.get('images-%s' % parser.get('general','arch'), 'kernel', '') == '':
            False
        if parser.get('images-%s' % parser.get('general','arch'), 'initrd', '') == '':
            False
        if int(parser.get('general', 'version').split('.')[0]) < 7:
            return False
        return parser

    def find_addon_repos(self, ks_meta):
        """
        using info from .treeinfo find addon repos
        """
        try:
            # Initialize ks_meta['repos'] if needed
            if 'repos' not in ks_meta:
                ks_meta['repos'] = []
            ks_meta['repos'].append('addons')
            addons = self.parser.get('general', 'addons')
            if addons:
                ks_meta['repos_addons'] = addons.split(',')
                for addon in ks_meta['repos_addons']:
                    ks_meta['repos_addons_%s' % addon] = os.path.join(
                                            self.options.repo_available_as,
                                            self.parser.get('addon-%s' % addon, 'repository')
                                                                     )
            return ks_meta
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
            logging.debug('no addon repos for %s, %s' % (self.parser.url,e))
            return ks_meta

    def get_kernel_path(self):
        return self.parser.get('images-%s' % self.tree['arch'],'kernel')

    def get_initrd_path(self):
        return self.parser.get('images-%s' % self.tree['arch'],'initrd')


def Build(url):
    for cls in Importer.__subclasses__():
        parser = cls.is_importer_for(url)
        if parser != False:
            logging.info("Importing: %s, using %s" % (url, cls.__name__))
            return cls(parser)
    raise BX('No valid importer found for %s' % url)

def main():
    parser = OptionParser()
    parser.add_option("-l", "--lab",
                      default="http://127.0.0.1/cobbler_api",
                      help="cobbler URI to use")
    parser.add_option("-c", "--add-distro-cmd",
                      default="/var/lib/beaker/addDistro.sh",
                      help="Command to run to add a new distro")
    parser.add_option("-n", "--name",
                      default=None,
                      help="Alternate name to use, otherwise we read it from .treeinfo")
    parser.add_option("-k", "--kickstart",
                      default=None,
                      help="Alternate kickstart to use")
    parser.add_option("-t", "--tag",
                      default=[],
                      action="append",
                      dest="tags",
                      help="Additional tags to add")
    parser.add_option("--root",
                      action='store_true',
                      default=False,
                      help="Add root=live: to kernel_options")
    parser.add_option("-a", "--available-as",
                      default='',
                      help="Location to use as install path. Required if using file://")
    parser.add_option("--repo-available-as",
                      default='',
                      help="Location to use as repo path. if not set and not using http:// no addon repos will be available for install")
    parser.add_option("--repo",
                      default=[],
                      dest="repos",
                      action="append",
                      help="full path to repo")
    parser.add_option("-r", "--run-jobs",
                      action='store_true',
                      default=False,
                      help="Run automated Jobs")
    parser.add_option("-v", "--debug",
                      action='store_true',
                      default=False,
                      help="show debug messages")
    parser.add_option("-q", "--quiet",
                      action='store_true',
                      default=False,
                      help="less messages")
                      
    (opts, args) = parser.parse_args()

    LOG_FORMAT = '%(asctime)s - %(levelname)s - %(filename)s - ' \
        '%(funcName)s:%(lineno)s - %(message)s'
    if opts.debug:
        LOG_LEVEL = logging.DEBUG
    elif opts.quiet:
        LOG_LEVEL = logging.CRITICAL
    else:
        LOG_LEVEL = logging.INFO
        LOG_FORMAT = '%(message)s'

    formatter = logging.Formatter(LOG_FORMAT)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger = logging.getLogger('')
    logger.addHandler(stdout_handler)
    logger.setLevel(LOG_LEVEL)

    if not args:
        logging.critical('No location specified!')
        sys.exit(10)
    url = args[0]
    # If available_as is specified as http or ftp and we didn't
    # specifiy repo-available-as then use available-as location
    # to serve repos from.
    if opts.available_as.startswith(('http','ftp')) and \
       not opts.repo_available_as:
        opts.repo_available_as = opts.available_as
    # If the user didn't specify repo-available-as or available-as
    # and url starts with http or ftp we can use that location 
    # to serve repos from.  
    if url.startswith(('http','ftp')) and not opts.repo_available_as:
        opts.repo_available_as = url
    if url.startswith('file://') and not opts.available_as:
        logging.critical('file:// requires available-as option to be set!')
        sys.exit(20)
    try:
        build = Build(url)
        build.process(opts)
    except BX, err:
        logging.critical(err)
        sys.exit(30)

if __name__ == '__main__':
    main()
