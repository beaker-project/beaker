
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pkg_resources
import urlparse
import re
import jinja2
import tempfile
import difflib
from sqlalchemy.orm.exc import NoResultFound
from bkr.inttest import data_setup, get_server_base
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.model import session, Distro, DistroTree, Arch, DistroTreeRepo

# This is the name of the system that is used when testing
# for an expected rendered kickstart. If you are using this
# system, be aware that other tests may also use it.
kickstart_system_fqdn = u'test01.test-kickstart.invalid'

def create_user():
    user = data_setup.create_user(password=u'password')
    user.root_password = '$1$beaker$yMeLK4p1IVkFa80RyTkpE.'
    return user

def create_lab_controller():
    return data_setup.create_labcontroller(
        fqdn=u'lab.test-kickstart.invalid')

def create_x86_64_automated(lab_controller):
    return data_setup.create_system(arch=u'x86_64',
        fqdn=kickstart_system_fqdn, status=u'Automated',
        lab_controller=lab_controller, return_existing=True)

def create_rhel62():
    try:
        return Distro.by_name(u'RHEL-6.2')
    except DatabaseLookupError:
        rhel62 = data_setup.create_distro(name=u'RHEL-6.2',
                osmajor=u'RedHatEnterpriseLinux6', osminor=u'2')
        return rhel62

def create_rhel62_server_x86_64(lab_controller):
    rhel62 = create_rhel62()
    x86_64 = Arch.by_name(u'x86_64')
    try:
        return DistroTree.query.filter_by(distro=rhel62, variant=u'Server', arch=x86_64).one()
    except NoResultFound:
        rhel62_server_x86_64 = data_setup.create_distro_tree(
                distro=rhel62, variant=u'Server', arch=u'x86_64',
                lab_controllers=[lab_controller],
                urls=[u'http://lab.test-kickstart.invalid/distros/RHEL-6.2/Server/x86_64/os/',
                      u'nfs://lab.test-kickstart.invalid:/distros/RHEL-6.2/Server/x86_64/os/'])
        rhel62_server_x86_64.repos[:] = [
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
        return rhel62_server_x86_64

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
    expected = expected.rstrip('\n')
    actual = actual.rstrip('\n')
    if expected != actual:
        expected_path = pkg_resources.resource_filename('bkr.inttest',
                'server/kickstarts/%s.expected' % name)
        diff = ''.join(difflib.ndiff(expected.splitlines(True), actual.splitlines(True)))
        raise AssertionError('Actual kickstart does not match expected %s\n%s'
                % (expected_path, diff))

def jinja_choice_loader(loader):
    return jinja2.ChoiceLoader([loader,
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
