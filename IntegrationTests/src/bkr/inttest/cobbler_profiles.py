import sys
import pkg_resources
from bkr.labcontroller.osversion import *

class Options(object):
    def __init__(self):
        self.only_beaker = False
        self.skip_beaker = False
        self.skip_jobs = False
        self.test_output_dir = pkg_resources.resource_filename(self.__module__,
                               'labcontroller/osversion_data')

class TestSchedulerProxy(SchedulerProxy):
    def __init__(self, options):
        pass

    def add_distro(self, distro):
        pass

    def run_distro_test_job(self, distro):
        pass

class TestCobblerProxy(CobblerProxy):
    def __init__(self, options):
        self.options = options
        # How should default_kickstart be handled?
        self.settings = dict(default_kickstart = "/var/lib/cobbler/kickstarts/sample.ks")

    def get_profiles_since(self, last_run, stage='pre'):
        # list files from filesystem, last_run will be ignored
        profiles = []
        for profile in  glob.glob(os.path.join(self.options.test_output_dir,
                                               'JSON',
                                               'profiles-%s' % stage,
                                               '*.json'
                                              )
                                 ):
            fd = open(profile, "r")
            profiles.append(simplejson.loads(fd.read(), encoding="utf-8"))
            fd.close()
        return profiles

    def get_distro(self, name, stage='pre'):
        distro = self.get_distro_profile(name, type='distros', stage=stage)
        distro['kernel'] = os.path.join(self.options.test_output_dir,
                                        distro['kernel'])
        distro['initrd'] = os.path.join(self.options.test_output_dir,
                                        distro['initrd'])
        return distro

    def get_profile(self, name, stage='pre'):
        return self.get_distro_profile(name, type='profiles', stage=stage)

    def get_distro_profile(self, name, type='distros', stage='pre'):
        # use json.decode to read the distro object back in.
        distro_profile = None
        dp_path = os.path.join(self.options.test_output_dir,
                                   'JSON',
                                   '%s-%s' % (type, stage),
                                   '%s.json' % name)
        if os.path.exists(dp_path):
            fd = open(dp_path, "r")
            distro_profile = simplejson.loads(fd.read(), encoding="utf-8")
        # hack
        if 'id' in distro_profile:
            distro_profile['id'] = None
        return distro_profile

    def get_profile_handle(self, profile_name):
        # no op
        pass

    def modify_profile(self, profile_id, profile_key, profile_value):
        # no op
        pass

    def save_profile(self, profile_id):
        # no op
        pass

    def get_last_run_time(self):
        return 0

    def set_last_run_time(self, timestamp):
        pass

class TestProfile(Profile):
    def save_data(self):
        pass

    def obfuscate(self):
        pass

class TestProfiles(Profiles):

    # override iterator to return a Test_Distro instead of a Distro
    def __iter__(self):
        if self.profiles:
            for profile in self.profiles:
                yield TestProfile(profile, self.lab)

class TestRcmProxy(RcmProxy):
    pass

class TestLabProxy(LabProxy):
    def __init__(self, options):
        self.options = options
        self.cobbler = TestCobblerProxy(options)
        self.scheduler = TestSchedulerProxy(options)
        self.capture_profile = None
        self.rcm = None

    # override to return a Test_Distros instead of a Distros
    def get_profiles_since_last_run(self):
        last_run = self.cobbler.get_last_run_time()
        profiles = self.cobbler.get_profiles_since(last_run)
        return TestProfiles(profiles, self)


def main():
    new_run = time.time()

    opts = Options()
    lab = TestLabProxy(opts)
    lab.process_profiles(new_run)

if __name__ == '__main__':
    main()
