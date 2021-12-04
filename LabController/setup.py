from setuptools import setup, find_packages
from glob import glob

try:
    from subprocess import getstatusoutput
except ImportError:
    from commands import getstatusoutput


def systemd_unit_dir():
    status, output = getstatusoutput('pkg-config --variable systemdsystemunitdir systemd')
    if status or not output:
        return None # systemd not found
    return output.strip()

def systemd_tmpfiles_dir():
    # There doesn't seem to be a specific pkg-config variable for this
    status, output = getstatusoutput('pkg-config --variable prefix systemd')
    if status or not output:
        return None # systemd not found
    return output.strip() + '/lib/tmpfiles.d'

data_files = [
    ('/etc/beaker/', ['labcontroller.conf']),
    ('/etc/beaker/power-scripts/', []),
    ('/etc/beaker/install-failure-patterns/', []),
    ('/etc/cron.hourly', ['cron.hourly/beaker_expire_distros']),
    ('/etc/sudoers.d', ['sudoers.d/beaker_proxy_clear_netboot']),
    ('/etc/httpd/conf.d', ['apache/beaker-lab-controller.conf']),
    ('/etc/rsyslog.d', ['rsyslog.d/beaker-lab-controller.conf']),
    # /etc/logrotate.d/beaker is in Server but applies to LCs too
    ('/var/lib/beaker', ['addDistro/addDistro.sh']),
    ('/var/lib/beaker/addDistro.d', glob('addDistro/addDistro.d/*')),
    ('/var/www/beaker/logs', []),
    ('/usr/share/bkr/lab-controller', ['apache/404.html'] + glob('extra/*')),
]
if systemd_unit_dir():
    data_files.extend([
        (systemd_unit_dir(), ['systemd/beaker-proxy.service',
                              'systemd/beaker-provision.service',
                              'systemd/beaker-watchdog.service',
                              'systemd/beaker-transfer.service']),
        (systemd_tmpfiles_dir(), ['tmpfiles.d/beaker-lab-controller.conf']),
        ('/run/beaker-lab-controller', []),
    ])

setup(
    name='beaker-lab-controller',
    version='29.1',
    description='Daemons for controlling a Beaker lab',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',

    install_requires=[
        'Flask',
    ],

    packages=find_packages('src'),
    package_dir = {'':'src'},

    namespace_packages = ['bkr'],

    data_files=data_files,
    package_data = {
        'bkr.labcontroller': [
            'default.conf',
            'power-scripts/*',
            'install-failure-patterns/*',
            'pxemenu-templates/*'
        ],
    },

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    ],

    entry_points = {
        'console_scripts': (
            'beaker-proxy    = bkr.labcontroller.main:main',
            'beaker-watchdog = bkr.labcontroller.watchdog:main',
            'beaker-transfer = bkr.labcontroller.transfer:main',
            'beaker-import = bkr.labcontroller.distro_import:main',
            'beaker-provision = bkr.labcontroller.provision:main',
            'beaker-pxemenu = bkr.labcontroller.pxemenu:main',
            'beaker-expire-distros = bkr.labcontroller.expire_distros:main',
            'beaker-clear-netboot = bkr.labcontroller.clear_netboot:main',
        ),
    }
)
