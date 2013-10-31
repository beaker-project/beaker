from setuptools import setup, find_packages
from glob import glob

setup(
    name = "bkr.labcontroller",
    version='0.14.2rc2',
    license = "GPLv2+",

    packages=find_packages('src'),
    package_dir = {'':'src'},

    namespace_packages = ['bkr'],

    data_files = [('/etc/beaker/', ['labcontroller.conf']),
                  ('/etc/beaker/power-scripts/', []),
                  ('/etc/init.d', ['init.d/beaker-proxy',
                                   'init.d/beaker-transfer',
                                   'init.d/beaker-provision',
                                   'init.d/beaker-watchdog']),
                  ('/etc/cron.hourly', ['cron.hourly/beaker_expire_distros']),
                  ('/etc/sudoers.d', ['sudoers.d/beaker_proxy_clear_netboot']),
                  ('/etc/httpd/conf.d', ['apache/beaker-lab-controller.conf']),
                  ('/etc/rsyslog.d', ['rsyslog.d/beaker-lab-controller.conf']),
                  # /etc/logrotate.d/beaker is in Server but applies to LCs too
                  ('/usr/lib/systemd/system',['systemd/beaker-proxy.service', 
                                              'systemd/beaker-provision.service',
                                              'systemd/beaker-watchdog.service',
                                              'systemd/beaker-transfer.service']),
                  ('/var/run/beaker-lab-controller', []),
                  ('/var/lib/beaker', ['addDistro/addDistro.sh']),
                  ('/var/lib/beaker/addDistro.d', glob('addDistro/addDistro.d/*')),
                  ('/var/www/beaker/logs', []),
                  ('/usr/share/bkr/lab-controller', ['apache/404.html'] +
                    glob('aux/*')),
                 ],
    package_data = {
        'bkr.labcontroller': [
            'default.conf',
            'power-scripts/*',
        ],
    },

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License (GPL)',
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
