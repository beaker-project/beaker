from setuptools import setup, find_packages
import glob
import re
import os
from distutils.dep_util import newer
from distutils import log

from distutils.command.build_py import build_py
from distutils.command.build_scripts import build_scripts as _build_scripts
from distutils.command.build import build as _build
from distutils.command.install_data import install_data as _install_data
from distutils.dep_util import newer
from setuptools.command.install import install as _install
from setuptools.command.install_lib import install_lib as _install_lib

description = (
  "Beaker is a system for full stack software integration testing "
  "(including hardware compatibility testing)."
)
author = "Red Hat, Inc."
email = "beaker-devel@lists.fedorahosted.org"
copyright = "2008-2013 Red Hat, Inc."
url = "http://beaker-project.org/"
license = "GPLv2+"

poFiles = filter(os.path.isfile, glob.glob('po/*.po'))

SUBSTFILES = ('bkr/server/config/app.cfg')

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

class InstallData(_install_data, object):

    def finalize_options(self):
        '''Override to emulate setuptools in the default case.
        install_data => install_dir
        '''
        self.temp_lib = None
        self.temp_data = None
        self.temp_prefix = None
        haveInstallDir = self.install_dir
        self.set_undefined_options('install',
                ('install_data', 'temp_data'),
                ('install_lib', 'temp_lib'),
                ('prefix', 'temp_prefix'),
                ('root', 'root'),
                ('force', 'force'),
                )
        if not self.install_dir:
            if self.temp_data == self.root + self.temp_prefix:
                self.install_dir = os.path.join(self.temp_lib, 'beaker')
            else:
                self.install_dir = self.temp_data

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
    ("/etc/init.d", ["init.d/beakerd"]),
    ("/etc/cron.d", ["cron.d/beaker"]),
    ("/etc/rsyslog.d", ["rsyslog.d/beaker-server.conf"]),
    ("/etc/logrotate.d", ["logrotate.d/beaker"]),
    ('/usr/lib/systemd/system',['systemd/beakerd.service']),
    ("/usr/share/bkr", filter(os.path.isfile, glob.glob("apache/*.wsgi"))),
    ("/var/log/beaker", []),
    ("/var/www/beaker/logs", []),
    ("/var/run/beaker", []),
    ("/var/www/beaker/rpms", []),
    ("/var/www/beaker/repos", []),
]
setup(
    name="bkr.server",
    namespace_packages = ['bkr'],
    version='0.14.2rc2',

    # uncomment the following lines if you fill them out in release.py
    description=description,
    author=author,
    author_email=email,
    url=url,
    #download_url=download_url,
    license=license,
    cmdclass = {
        'build': Build,
        'build_py': build_py_and_kid,
        'install_data': InstallData,
    },
    install_requires=[
        'TurboGears >= 1.1',
        'sqlalchemy >= 0.6',
    ],
    scripts=[],
    zip_safe=False,
    data_files = data_files,
    packages = find_packages(),
    package_data={
        'bkr.server.config': ['*.cfg'],
        'bkr.server.templates': ['*.kid'],
        'bkr.server': ['kickstarts/*', 'snippets/*', 'reporting-queries/*'],
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
        'turbogears.identity.provider': (
            'ldapsa = bkr.server.identity:LdapSqlAlchemyIdentityProvider'
        ),
        'console_scripts': (
            'start-beaker = bkr.server.commands:start',
            'beaker-init = bkr.server.tools.init:main',
            'product-update = bkr.server.tools.product_update:main',
            'beakerd = bkr.server.tools.beakerd:main',
            'nag-mail = bkr.server.tools.nag_email:main',
            'log-delete = bkr.server.tools.log_delete:main',
            'beaker-check = bkr.server.tools.check_beaker:main',
            'beaker-cleanup-visits = bkr.server.tools.cleanup_visits:main',
            'beaker-refresh-ldap = bkr.server.tools.refresh_ldap:main',
            'beaker-repo-update = bkr.server.tools.repo_update:main',
            'beaker-sync-tasks = bkr.server.tools.sync_tasks:main'
        ),
    }
    )

