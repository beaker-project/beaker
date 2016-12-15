__requires__ = ['CherryPy < 3.0']

from setuptools import setup, find_packages
import glob
import re
import os
import commands
from distutils import log
from distutils.core import Command
from distutils.util import change_root
from distutils.command.build_py import build_py
from distutils.command.build import build as _build
from setuptools.command.install import install as _install

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Common'))
sys.path.insert(1, os.path.dirname(__file__))

poFiles = filter(os.path.isfile, glob.glob('po/*.po'))

SUBSTFILES = ('bkr/server/config/app.cfg')

def systemd_unit_dir():
    status, output = commands.getstatusoutput('pkg-config --variable systemdsystemunitdir systemd')
    if status or not output:
        return None # systemd not found
    return output.strip()

def systemd_tmpfiles_dir():
    # There doesn't seem to be a specific pkg-config variable for this
    status, output = commands.getstatusoutput('pkg-config --variable prefix systemd')
    if status or not output:
        return None # systemd not found
    return output.strip() + '/lib/tmpfiles.d'

class Build(_build, object):
    '''
    Build the package, changing the directories that data files are installed.
    '''
    user_options = _build.user_options
    user_options.extend([('install-data=', None,
        'Installation directory for data files')])
    # These are set in finalize_options()
    substitutions = {'@DATADIR@': None, '@LOCALEDIR@': None}
    subRE = re.compile('(' + '|'.join(substitutions.keys()) + ')+')

    def initialize_options(self):
        self.install_data = None
        super(Build, self).initialize_options()
    def finalize_options(self):
        if self.install_data:
            self.substitutions['@DATADIR@'] = self.install_data + '/bkr/server'
            self.substitutions['@LOCALEDIR@'] = self.install_data + '/locale'
        else:
            self.substitutions['@DATADIR@'] = '%(top_level_dir)s'
            self.substitutions['@LOCALEDIR@'] = '%(top_level_dir)s/../locale'
        super(Build, self).finalize_options()

    def run(self):
        '''Substitute special variables for our installation locations.'''
        for filename in SUBSTFILES:
            # Change files to reference the data directory in the proper
            # location
            infile = filename + '.in'
            if not os.path.exists(infile):
                continue
            try:
                f = file(infile, 'r')
            except IOError:
                if not self.dry_run:
                    raise
                f = None
            outf = file(filename, 'w')
            for line in f.readlines():
                matches = self.subRE.search(line)
                if matches:
                    for pattern in self.substitutions:
                        line = line.replace(pattern,
                                            self.substitutions[pattern])
                outf.writelines(line)
            outf.close()
            f.close()

        # Make empty en.po
        dirname = 'locale/'
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        #shutil.copy('po/LINGUAS', 'locale/')

        for pofile in poFiles:
            # Compile PO files
            lang = os.path.basename(pofile).rsplit('.', 1)[0]
            dirname = 'locale/%s/LC_MESSAGES/' % lang
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            # Hardcoded gettext domain: 'server'
            mofile = dirname + 'server' + '.mo'
            subprocess.call(['/usr/bin/msgfmt', pofile, '-o', mofile])
        super(Build, self).run()

# from http://trac.turbogears.org/changeset/6869
class build_py_and_kid(build_py):
    """Build pure Python modules and Kid templates."""

    def byte_compile(self, files):
        """Byte-compile all Python modules and all Kid templates."""
        build_py.byte_compile(self, files)
        kid_files = [f for f in files if f.endswith('.kid')]
        if not kid_files:
            return
        from distutils import log
        try:
            from kid.compiler import compile_file
        except ImportError:
            log.warn("Kid templates cannot be compiled,"
                " because Kid is not installed.")
            return
        if self.dry_run:
            return
        for kid_file in kid_files:
            if compile_file(kid_file, force=self.force):
                log.info("byte-compiling %s", kid_file)
            else:
                log.debug("skipping byte-compilation of %s", kid_file)

class Install(_install):
    sub_commands = _install.sub_commands + [
        ('install_assets', None),
    ]

class InstallAssets(Command):
    description = 'install web assets'
    user_options = []

    def initialize_options(self):
        self.install_data = None

    def finalize_options(self):
        self.set_undefined_options('install', ('install_data', 'install_data'))
        self.install_dir = os.path.join(self.install_data, 'bkr/server/assets')
        self.source_dir = 'assets'

    def run(self):
        from bkr.server import assets
        for filename in assets.list_asset_sources(self.source_dir):
            source_path = os.path.join(self.source_dir, filename)
            dest_path = os.path.join(self.install_dir, filename)
            self.mkpath(os.path.dirname(dest_path), mode=0755)
            self.copy_file(source_path, dest_path)


def find_data_recursive(dest_dir, src_dir, exclude=frozenset()):
    if src_dir[-1] != '/':
        src_dir = src_dir + '/'
    for dirpath, dirnames, filenames in os.walk(src_dir):
        assert dirpath.startswith(src_dir)
        yield (os.path.join(dest_dir, dirpath[len(src_dir):]),
               [os.path.join(dirpath, filename) for filename in filenames
                if filename not in exclude])

data_files = \
    list(find_data_recursive('bkr/server/static', 'bkr/server/static/')) + [
    ("/etc/beaker", ["server.cfg"]),
    ("/etc/httpd/conf.d", ["apache/beaker-server.conf"]),
    ("/etc/cron.d", ["cron.d/beaker"]),
    ("/etc/rsyslog.d", ["rsyslog.d/beaker-server.conf"]),
    ("/etc/logrotate.d", ["logrotate.d/beaker"]),
    ("/usr/share/bkr", filter(os.path.isfile, glob.glob("apache/*.wsgi"))),
    ("/var/log/beaker", []),
    ("/var/cache/beaker/assets", []),
    ("/var/www/beaker/logs", []),
    ("/var/www/beaker/rpms", []),
    ("/var/www/beaker/repos", []),
]
if systemd_unit_dir():
    data_files.extend([
        (systemd_unit_dir(), ['systemd/beakerd.service']),
        (systemd_tmpfiles_dir(), ['tmpfiles.d/beaker-server.conf']),
        ('/run/beaker', []),
    ])
else:
    data_files.extend([
        ('/etc/init.d', ['init.d/beakerd']),
        ('/var/run/beaker', []),
    ])
setup(
    name='beaker-server',
    namespace_packages = ['bkr'],
    version='23.3',
    description='Beaker scheduler and web interface',
    long_description=
        'Beaker is a system for full stack software integration testing '
        '(including hardware compatibility testing).',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',
    cmdclass = {
        'build': Build,
        'build_py': build_py_and_kid,
        'install': Install,
        'install_assets': InstallAssets,
    },
    install_requires=[
        'TurboGears >= 1.1',
        'sqlalchemy >= 0.6',
        'Flask',
    ],
    scripts=[],
    zip_safe=False,
    data_files = data_files,
    packages = find_packages(),
    package_data={
        'bkr.server.tests': ['unit-test.cfg', '*.rpm'],
        'bkr.server.config': ['*.cfg'],
        'bkr.server.templates': ['*.kid'],
        'bkr.server': [
            'data-migrations/*',
            'kickstarts/*',
            'snippets/*',
            'reporting-queries/*/*.sql',
            'reporting-queries/*.sql',
            'mail-templates/*',
        ],
        'bkr.server.alembic': ['versions/*.py', 'env.py'],
    },
    keywords=[
        'turbogears.app',
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Framework :: TurboGears',
        'Framework :: TurboGears :: Applications',
        'License :: OSI Approved :: GNU General Public License (GPL)',
    ],
    test_suite='nose.collector',
    entry_points = {
        'console_scripts': (
            'beaker-init = bkr.server.tools.init:main',
            'product-update = bkr.server.tools.product_update:main',
            'beakerd = bkr.server.tools.beakerd:main',
            'beaker-usage-reminder = bkr.server.tools.usage_reminder:main',
            'beaker-log-delete = bkr.server.tools.log_delete:main',
            'beaker-create-ipxe-image = bkr.server.tools.ipxe_image:main',
            'beaker-refresh-ldap = bkr.server.tools.refresh_ldap:main',
            'beaker-repo-update = bkr.server.tools.repo_update:main',
            'beaker-sync-tasks = bkr.server.tools.sync_tasks:main',
            'beaker-create-kickstart = bkr.server.tools.create_kickstart:main'
        ),
    }
    )

