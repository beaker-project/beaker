
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
    name='beaker-client',
    version='24.1',
    description='Command-line client for interacting with Beaker',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',

    install_requires=[
        'beaker-common',
        'lxml',
        'requests',
        'PrettyTable',
        'Jinja2',
    ],

    packages=find_packages('src'),
    package_dir = {'':'src'},

    package_data = {
        'bkr.client': ['host-filters/*']
        },
    namespace_packages = ['bkr'],

    data_files = [
        ('/etc/beaker', []),
        (bash_completion_dir(), ['bash-completion/bkr']),
    ],

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.6',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    ],

    entry_points = {
        'console_scripts': (
            'bkr = bkr.client.main:main',
            'beaker-wizard = bkr.client.wizard:main',
        ),
    },
)
