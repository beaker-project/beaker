import unittest
import time
from bkr.inttest import cobbler_profiles


opts = cobbler_profiles.Options()
lab = cobbler_profiles.TestLabProxy(opts)
profiles = lab.process_profiles(time.time())


def check_even(a, b):
    assert a.distro == b.distro, '%s != %s' % (a.distro, b.distro)
    assert a.profile == b.profile, '%s != %s' % (a.profile, b.profile)
    assert a.xtras == b.xtras, '%s != %s' % (a.xtras, b.xtras)


class Post(object):
    def __init__(self, profile):
        self.distro = lab.cobbler.get_distro(profile.distro.get('name'),
                                             stage='post')
        self.profile = lab.cobbler.get_profile(profile.profile.get('name'),
                                              stage='post')
        self.xtras = lab.cobbler.get_distro_profile(profile.profile.get('name'),
                                                    type='xtras', stage='post')


def test_round_trip():
    for profile in profiles:
        post = Post(profile)
        check_even.description = '%s == post' % profile.profile.get('name')
        yield check_even, profile, post

