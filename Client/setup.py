
import sys
import commands
from glob import glob
from setuptools import setup, find_packages
from distutils.command.build import build as _build

def bash_completion_dir():
    status, output = commands.getstatusoutput('pkg-config --variable completionsdir bash-completion')
    if status or not output:
        return '/etc/bash_completion.d'
    return output.strip()

setup(
    name = "bkr.client",
    version='0.16.0',
    license = "GPLv2+",

    packages=find_packages('src'),
    package_dir = {'':'src'},

    namespace_packages = ['bkr'],

    data_files = [
        ('/etc/beaker', []),
        (bash_completion_dir(), ['bash-completion/bkr']),
    ],

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'License :: OSI Approved :: GNU General Public License (GPL)',
    ],

    entry_points = {
        'console_scripts': (
            'bkr = bkr.client.main:main',
            'beaker-wizard = bkr.client.wizard:main',
        ),
    },
)
