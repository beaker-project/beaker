
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from setuptools import setup, find_packages

try:
    from commands import getstatusoutput
except ImportError:
    from subprocess import getstatusoutput


def bash_completion_dir():
    status, output = getstatusoutput(
        'pkg-config --variable completionsdir bash-completion')
    if status or not output:
        return '/etc/bash_completion.d'
    return output.strip()


setup(
    name='beaker-client',
    version='28.3',
    description='Command-line client for interacting with Beaker',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',

    install_requires=[
        'beaker-common',
        'lxml',
        'six',
        'requests',
        'PrettyTable',
        'Jinja2',
        'gssapi'
    ],

    packages=find_packages('src'),
    package_dir={'': 'src'},

    package_data={
        'bkr.client': ['host-filters/*']
    },
    namespace_packages=['bkr'],

    data_files=[
        ('/etc/beaker', []),
        (bash_completion_dir(), ['bash-completion/bkr']),
    ],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    ],

    entry_points={
        'console_scripts': (
            'bkr = bkr.client.main:main',
            'beaker-wizard = bkr.client.wizard:main',
        ),
    },
)
