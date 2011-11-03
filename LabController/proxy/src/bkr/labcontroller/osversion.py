import sys, os
import time
import re
import glob
import xmlrpclib
import string
import ConfigParser
import getopt
from optparse import OptionParser
import shutil
import simplejson
import copy

class ProfileDecodeError(ValueError):
    pass

class SchedulerProxy(object):
    """Scheduler Proxy"""
    def __init__(self, options):
        self.add_distro_cmd = options.add_distro_cmd
        # addDistroCmd = '/var/lib/beaker/addDistro.sh'
        self.force = options.force
        self.proxy = xmlrpclib.ServerProxy('http://localhost:8000',
                                           allow_none=True)

    def add_distro(self, distro):
        if distro.has_changed or self.force:
            return self.proxy.addDistro(distro.flatten)
        else:
            return False

    def run_distro_test_job(self, distro):
        if self.is_add_distro_cmd and \
           distro.is_wellformed and \
           distro.has_changed:
            cmd = self._make_add_distro_cmd(distro)
            os.system(cmd)
            return cmd
        return False

    def _make_add_distro_cmd(self, distro):
        #addDistro.sh "rel-eng" RHEL6.0-20090626.2 RedHatEnterpriseLinux6.0 x86_64 "Default"
        cmd = '%s "%s" %s %s %s "%s"' % (
            self.add_distro_cmd,
            ','.join(distro.distro.get('tags',[])),
            distro.xtras.get('treename'),
            '%s.%s' % (
            distro.xtras.get('osmajor'),
            distro.xtras.get('osminor')),
            distro.distro.get('arch'),
            distro.xtras.get('variant', ''))
        return cmd


    @property
    def is_add_distro_cmd(self):
        # Kick off jobs automatically
        if os.path.exists(self.add_distro_cmd):
            return True
        return False


class RcmProxy(object):
    def __init__(self, rcm_xmlrpc_host):
	return xmlrpclib.ServerProxy(rcm_xmlrpc_host)


class CobblerProxy(object):
    def __init__(self, options):
        from cobbler import utils
        self.cobbler = xmlrpclib.ServerProxy(options.lab)
        #cobbler = xmlrpclib.ServerProxy('http://127.0.0.1/cobbler_api')
        self.token = self.cobbler.login("", utils.get_shared_secret())
        self.settings = self.cobbler.get_settings(self.token)

        self.filename = self.settings.get('beaker_lab_controller_osversion.mtime_filename', '/var/run/beaker-lab-controller/osversion.mtime')
        self.force = options.force

    def get_profiles_since(self, last_run):
        return self.cobbler.get_profiles_since(last_run)

    def get_distro(self, distro_name):
        return self.cobbler.get_distro(distro_name, False, self.token)

    def get_profile_handle(self, profile_name):
        return self.cobbler.get_profile_handle(profile_name, self.token)

    def modify_profile(self, profile_id, profile_key, profile_value):
        self.cobbler.modify_profile(profile_id, profile_key, profile_value, self.token)
        #cobbler.modify_profile(profile_id, 'kickstart', kickstart, self.token)

    def save_profile(self, profile_id):
        self.cobbler.save_profile(profile_id, self.token)

    def get_last_run_time(self):
        #self.filename = "/var/run/beaker-lab-controller/osversion.mtime"
        last_run = 0.0
        if os.path.exists(self.filename) and not self.force:
            last_run = float(open(self.filename).readline())

        return last_run

    def set_last_run_time(self, timestamp):
        FH = open(self.filename, "w")
        FH.write('%s' % timestamp)
        FH.close()


class Profile(object):
    """
    Now supports just copying the profile to have a new install based on
    a different kickstart
    cobbler profile copy --name RHEL6-GOLD-Server-x86_64 \
                         --newname MRG-6.0-Server-x86_64 \
                         --comment='{"treename" : "MRG-6.0"}' \
                         --kickstart=/var/lib/cobbler/kickstarts/mrg-6.ks
    """
    def __init__(self, profile, lab):
        self.has_changed = False
        self.profile = profile
        self.lab = lab
        self.profile['id'] = self.get_profile_handle(self.profile.get('name'))
        self.kickbase = os.path.dirname(lab.cobbler.settings.get('default_kickstart'))
        #self.kickbase = "/var/lib/cobbler/kickstarts"
        self.distro = self.get_distro(profile.get('distro'))
        try:
            self.xtras = simplejson.loads(self.profile['comment'], encoding="utf-8")
        except ValueError:
            self.xtras = dict()
        self.tree_path = self._get_tree_path()
        self.compose_path = self._get_compose_path()
        self._update_xtras()

    @property
    def is_wellformed(self):
        if self.distro.get('ks_meta').get('tree') and \
           self.xtras.get('osmajor') and \
           self.xtras.get('osminor'):
            return True
        return False

    @property
    def has_rcm_treename(self):
        if self.xtras.get('treename') and \
           self.distro.get('ks_meta').get('tree'):
            return True
        return False

    @property
    def is_ignore(self):
        return self.profile.get('comment','').find('ignore') != -1

    @property
    def is_xen(self):
        return self.distro.get('name').find('-xen-') != -1

    @property
    def flatten(self):
        mydict = dict(self.distro.items() + self.xtras.items())
        # We want all the distro attributes like arch but we want to use
        # the profile name so we override the name from distro with profile's
        mydict['name'] = self.profile.get('name')
        return mydict

    def get_profile_handle(self, profile_name):
        return self.lab.cobbler.get_profile_handle(profile_name)

    def get_distro(self, distro_name):
        return self.lab.cobbler.get_distro(distro_name)

    def modify_profile(self, profile_id, profile_key, profile_value):
        self.has_changed = True
        self.lab.cobbler.modify_profile(profile_id, profile_key, profile_value)
        self.lab.cobbler.save_profile(profile_id)

    def update_cobbler_kickstart(self):
        kickstart = None
        # Only update kickstart if its empty or
        # pointing to sample.ks or legacy.ks
        pkickstart = self.profile.get('kickstart','')
        if pkickstart.endswith('sample.ks') or \
           pkickstart.endswith('legacy.ks') or \
           pkickstart == '':
            kickstart = self._find_kickstart(
                                        self.distro.get('arch'),
                                        self.xtras.get('osmajor'),
                                        self.xtras.get('osminor')
                                       )

        if kickstart:
            # Update our version so we can record it for unit tests.
            # Hmm.. Maybe we should just refetch this from cobbler at
            # the end?
            self.profile['kickstart'] = kickstart
            # Update cobblers version
            self.modify_profile(self.profile['id'], 'kickstart', kickstart)
            return True
        else:
            return False

    def _find_kickstart(self, arch, family, update):
        flavor = family.strip('0123456789')
        kickstarts = [
               "%s/%s/%s.%s.ks" % (self.kickbase, arch, family, update),
               "%s/%s/%s.ks" % (self.kickbase, arch, family),
               "%s/%s/%s.ks" % (self.kickbase, arch, flavor),
               "%s/%s.%s.ks" % (self.kickbase, family, update),
               "%s/%s.ks" % (self.kickbase, family),
               "%s/%s.ks" % (self.kickbase, flavor),
               "%s/%s/default.ks" % (self.kickbase, arch),
               "%s/%s.ks" % (self.kickbase, family),
        ]
        for kickstart in kickstarts:
            if os.path.exists(kickstart):
                return kickstart
        return None


    def _update_xtras(self):
        # create parsers
        treeinfo_parser = MyConfigParser("%s/.treeinfo" % self.tree_path)
        composeinfo_parser = MyConfigParser("%s/.composeinfo" % self.compose_path)
        labels = treeinfo_parser.get('general', 'label')
        self.xtras['tags'] = self.xtras.get('tags') or \
                                     map(string.strip,
                                     labels and labels.split(',') or [])
        family  = treeinfo_parser.get('general', 'family').replace(" ","")
        version = treeinfo_parser.get('general', 'version').replace("-",".")
        self.xtras['variant'] = self.xtras.get('variant') or \
                                        treeinfo_parser.get('general', 'variant')
        self.xtras['osmajor'] = self.xtras.get('osmajor') or \
                                      "%s%s" % (family, version.split('.')[0])
        if version.find('.') != -1:
            self.xtras['osminor'] = self.xtras.get('osminor') or \
                                       version.split('.')[1]
        else:
            self.xtras['osminor'] = self.xtras.get('osminor') or 0


        # Use the name of the tree from .composeinfo if it exists.
        self.xtras['treename'] = self.xtras.get('treename') or \
                                         composeinfo_parser.get('tree', 'name',
                                         self.profile['name'].split('_')[0])

        arches = composeinfo_parser.get('tree', 'arches')
        self.xtras['arches'] = self.xtras.get('arches') or \
                                      map(string.strip,
                                      arches and arches.split(',') or [])

    def _get_tree_path(self):
        """
        Given a distro we will look at the kernel path and work backwards
        to find a .treeinfo file.

        Accepts distro dictionary
        Returns the path where .treeinfo lives or None
        """
 
        kerneldir = self.distro.get('kernel')
        while kerneldir != '/' and kerneldir != '':
            if os.path.exists('%s/.treeinfo' % kerneldir):
                return kerneldir
            kerneldir = os.path.dirname(kerneldir)

        raise ProfileDecodeError("Missing .treeinfo")

    def _get_compose_path(self):
        """
        Given a distro we will look at the kernel path and work backwards
        to find a .composeinfo file.

        Accepts distro dictionary
        Returns the path where .composeinfo lives or None
        """

        kerneldir = self.distro.get('kernel')
        while kerneldir != '/' and kerneldir != '':
            if os.path.exists('%s/.composeinfo' % kerneldir):
                return kerneldir
            kerneldir = os.path.dirname(kerneldir)

        raise ProfileDecodeError("Missing .composeinfo")

    def update_repos(self):

        repos = self._read_repos()

        updated_repos = False
        if repos.get('os') and not self.profile['ks_meta'].get('os_repos'):
            self.profile['ks_meta']['os_repos'] = '|'.join(repos['os'])
            updated_repos = True
        if repos.get('debug') and not self.profile['ks_meta'].get('debug_repos'):
            self.profile['ks_meta']['debug_repos'] = '|'.join(repos['debug'])
            updated_repos = True

        if updated_repos:
            self.modify_profile(self.profile['id'],
                               'ksmeta',
                               self.profile['ks_meta'])
            return True

        return False

    def _read_repos(self):

        if not self.tree_path:
            return dict()

        os_repos = []
        debug_repos = []
        repo_path_re = re.compile(r'%s/(.*)/repodata' % self.tree_path)


        # If rcm is defined we can ask what repos are defined for this tree
        if self.lab.rcm is not None:
            distro_path = self.tree_path
            prepos = []
            while distro_path != '':
                distro_path = '/'.join(distro_path.split('/')[1:])
                if not distro_path:
                    break
                try:
                    prepos = self.lab.rcm.tree_repos(distro_path)
                    break
                except xmlrpclib.ResponseError:
                    pass
            prepos.sort()
            for prepo in prepos:
                repo = os.path.join(self.tree_path, prepos[prepo], 'repodata')
                if os.path.exists(repo):
                    if 'debug' in repo:
                        debuginfo_repos.append('beaker-%s,%s' %
                                        (prepo,
                                         os.path.join(self.distro['ks_meta']['tree'],
                                         repo_path_re.search(repo).group(1),
                                                     )
                                        )
                                              )
                    else:
                        os_repos.append('beaker-%s,%s' %
                                        (prepo,
                                         os.path.join(self.distro['ks_meta']['tree'],
                                         repo_path_re.search(repo).group(1),
                                                     )
                                        )
                                       )
        # rcm is not avaialble, fall back to glob...
        else:
            os_repos = ['beaker-%s,%s' %
                                 (os.path.basename(os.path.dirname(repo)),
                                  os.path.join(self.distro['ks_meta']['tree'],
                                               repo_path_re.search(repo).group(1)),
                                 ) for repo in \
                         glob.glob(os.path.join(self.tree_path,
                                       "*/repodata")
                                  ) + \
                         glob.glob(os.path.join(self.tree_path,
                                       "../repo-*%s*/repodata" % self.xtras['variant'])
                                  )
                       ]
            os_repos.sort()
            debug_repos = ['beaker-%s,%s' %
                                 (os.path.basename(os.path.dirname(repo)),
                                  os.path.join(self.distro['ks_meta']['tree'],
                                               repo_path_re.search(repo).group(1)),
                                 ) for repo in \
                               glob.glob(os.path.join(self.tree_path,
                                       "../debug*/repodata")
                                  )
                          ]
            debug_repos.sort()
        return dict(os = os_repos, debug = debug_repos)

    def save_data(self):
        comment = simplejson.dumps(self.xtras, encoding="utf-8")
        if self.profile['comment'] != comment:
            self.profile['comment'] = comment

            self.modify_profile(self.profile['id'],
                                'comment',
                                self.profile['comment'])

    def obfuscate(self):
        """
        Return a copy of the distro object that has been clensed of any
        private data.
        """
        obfuscated = Profile(copy.deepcopy(self.profile), self.lab)
        obfuscated.compose_path = os.path.join('.',
                                               self.distro.get('name'),
                                              )
        obfuscated.tree_path = os.path.join(obfuscated.compose_path,
                                            self.distro.get('arch'),
                                            'os')
        obfuscated.distro['kernel'] = self.distro.get('kernel').replace(
                                         self.tree_path,
                                         obfuscated.tree_path)
        obfuscated.distro['initrd'] = self.distro.get('initrd').replace(
                                         self.tree_path,
                                         obfuscated.tree_path)
        obfuscated.distro['ks_meta']['tree'] = obfuscated.tree_path
        if 'debug_repos' in self.profile['ks_meta']:
            obfuscated.profile['ks_meta']['debug_repos'] = self.profile['ks_meta'].\
                   get('debug_repos').replace(self.distro['ks_meta'].get('tree'),
                                        obfuscated.distro['ks_meta'].get('tree')
                                             )
        if 'os_repos' in self.profile['ks_meta']:
            obfuscated.profile['ks_meta']['os_repos'] = self.profile['ks_meta'].\
                   get('os_repos').replace(self.distro['ks_meta'].get('tree'),
                                     obfuscated.distro['ks_meta'].get('tree')
                                          )
        return obfuscated


class MyConfigParser(object):
    def __init__(self, config):
        self.parser = None
        if os.path.exists(config):
            self.parser = ConfigParser.ConfigParser()
            try:
                self.parser.read(config)
            except ConfigParser.MissingSectionHeaderError, e:
                self.parser = None

    def get(self, section, key, default=''):
        if self.parser:
            try:
                default = self.parser.get(section, key)
            except (ConfigParser.NoSectionError, ConfigParser.NoOptionError), e:
                pass
        return default


class Profiles(object):
    def __init__(self, profiles, lab):
        self.profiles = profiles
        self.lab = lab

    # iterator
    def __iter__(self):
        if self.profiles:
            for profile in self.profiles:
                try:
                    yield Profile(profile, self.lab)
                except ProfileDecodeError, e:
                    sys.stderr.write("WARN: Profile %s, %s\n" % (profile.get('name'),e))


class CaptureProfile(object):
    def __init__(self, test_output_dir):
        self.test_output_dir = test_output_dir
        if not os.path.exists(self.test_output_dir):
            raise ValueError("%s does not exist" % self.test_output_dir)

    def to_filesystem(self, profile, obfs_profile):
        """ Capture .treeinfo, ramdisk location, kernel location
        """
        compose_file = os.path.join(profile.compose_path,
                                    '.composeinfo')
        obfs_compose_file = os.path.join(self.test_output_dir,
                                         obfs_profile.compose_path,
                                         '.composeinfo')
        if os.path.exists(compose_file) and \
           not os.path.exists(obfs_compose_file):
            verify_output_dir(os.path.join(self.test_output_dir,
                                         obfs_profile.compose_path)
                           )
            shutil.copyfile(compose_file, obfs_compose_file)

        treeinfo_file = os.path.join(profile.tree_path,
                                     '.treeinfo')
        obfs_treeinfo_file = os.path.join(self.test_output_dir,
                                          obfs_profile.tree_path,
                                          '.treeinfo')
        if os.path.exists(treeinfo_file) and \
           not os.path.exists(obfs_treeinfo_file):
            verify_output_dir(os.path.join(self.test_output_dir,
                                         obfs_profile.tree_path)
                           )
            shutil.copyfile(treeinfo_file, obfs_treeinfo_file)

        kernel_file = os.path.join(self.test_output_dir,
                                   obfs_profile.distro.get('kernel'))
        touch_file(kernel_file)
        # Create dummy kernel in /destination/obfuscated_path/kernel_path/kernel
        initrd_file = os.path.join(self.test_output_dir,
                              obfs_profile.distro.get('initrd'))
        touch_file(initrd_file)
        # Create dummy initrd in /destination/obfuscated_path/initrd_path/initrd

    def to_filesystem_post(self, obfs_profile):
        """ Capture repodata
        """
        for repo in ['os_repos', 'debug_repos']:
            if repo in obfs_profile.profile['ks_meta']:
                for os_repo in obfs_profile.profile['ks_meta'][repo].split('|'):
                    (repo_name, repo_path) = os_repo.split(',')
                    touch_file('%s/%s/%s' % (self.test_output_dir,
                                           repo_path,
                                           'repodata'))
        # Capture dummy repodata

    def to_datastruct(self, obfs, stage, dir_path, name):
        """ serialize profile to opts['test-output-dir'] + stage
        """
        json_file = os.path.join(self.test_output_dir,
                                   'JSON',
                                   '%s-%s' % (dir_path, stage),
                                   name + '.json')
        verify_output_dir(os.path.dirname(json_file))
        fd = open(json_file, "w+")
        fd.write(simplejson.dumps(obfs, encoding="utf-8"))
        fd.close()

    def all_to_datastruct(self, obfs_profile, stage):
        """ serialize profile to opts['test-output-dir'] + stage
        """
        datastructs = [ (obfs_profile.profile,
                         'profiles',
                         obfs_profile.profile.get('name')),
                        (obfs_profile.distro,
                         'distros',
                         obfs_profile.distro.get('name')),
                      ]
        if stage == 'post':
            datastructs.append(
                        (obfs_profile.xtras,
                         'xtras',
                         obfs_profile.profile.get('name'))
                              )
        for (obfs, dir_path, name) in datastructs:
            self.to_datastruct(obfs, stage, dir_path, name)


class LabProxy(object):
    def __init__(self, options):
        self.capture_profile = None
        self.rcm = None
        self.options = options
        self.cobbler = CobblerProxy(options)
        rcm_xmlrpc_host = self.cobbler.settings.get('rcm_xmlrpc_host')
        if rcm_xmlrpc_host:
            self.rcm = RcmProxy(rcm_xmlrpc_host)
        self.scheduler = SchedulerProxy(options)
        if self.options.test_output_dir:
            self.capture_profile = CaptureProfile(self.options.test_output_dir)

    def get_profiles_since_last_run(self):
        last_run = self.cobbler.get_last_run_time()
        profiles = self.cobbler.get_profiles_since(last_run)
        return Profiles(profiles, self)


    def process_profiles(self, new_run):

        profiles = self.get_profiles_since_last_run()
        processed_profiles = []

        for profile in profiles:
            print "Profile: %s" % profile.profile.get('name')

            # Skip trees without treename
            if not profile.has_rcm_treename:
                print "\tSkipping, no treename"
                continue

            # Skip ignored Distros
            if profile.is_ignore:
                print "\tProfile['comment'] == 'ignore', Skipping."
                continue

            # Skip xen Distros
            if profile.is_xen:
                print "\tSkipping, Xen distro"
                continue

            # if capture_profile is defined record this so
            # we can use it for unit test seed data
            if self.capture_profile:
                self.capture_profile.to_filesystem(profile, profile.obfuscate())
                self.capture_profile.all_to_datastruct(profile.obfuscate(), 'pre')

            print "\tUpdate Kickstart: %s" % profile.update_cobbler_kickstart()
            print "\tUpdate Repos: %s" % profile.update_repos()

            # Add distro to Beaker
            print "\tAdding to Beaker: %s" % self.scheduler.add_distro(profile)
            # If capture_profile is defined then capture what we processed
            # to be used for expected results in unit tests
            if self.capture_profile:
                self.capture_profile.to_filesystem_post(profile.obfuscate())
                self.capture_profile.all_to_datastruct(profile.obfuscate(), 'post')
            # Run any automated jobs
            print "\tAutomated Job: %s" % self.scheduler.run_distro_test_job(profile)

            profile.save_data()
            processed_profiles.append(profile)
        self.cobbler.set_last_run_time(new_run)
        return processed_profiles

def verify_output_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def touch_file(filename):
    verify_output_dir(os.path.dirname(filename))
    fd = open(filename, "w+")
    fd.close()


def main():
    parser = OptionParser()
    parser.add_option("-f", "--force", action="store_true", default=False,
                      help="Force all distros to be pushed again")
    parser.add_option("-l", "--lab",
                      default="http://127.0.0.1/cobbler_api",
                      help="cobbler URI to use")
    parser.add_option("-c", "--add_distro_cmd",
                      default="/var/lib/beaker/addDistro.sh",
                      help="Command to run to add a new distro")
    parser.add_option("-t", "--test-output-dir",
                      help="Capture distro data for unit tests. Argument is where on the filesystem to store the data")
    (opts, args) = parser.parse_args()

    new_run = time.time()

    try:
        lab = LabProxy(opts)
        lab.process_profiles(new_run)
    except Exception, e:
        sys.stderr.write("%s\n" % e)

if __name__ == '__main__':
    main()
