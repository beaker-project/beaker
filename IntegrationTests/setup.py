import fnmatch
import os
from glob import glob
from setuptools import setup, find_packages

def get_compose_layout():
    matches = []
    for root, dirnames, filenames in os.walk('src/bkr/inttest/labcontroller/compose_layout'):
      for filename in fnmatch.filter(filenames, '*'):
          matches.append(os.path.join(root.replace('src/bkr/inttest/', ''), filename))
    return matches

setup(
    name='bkr.inttest',
    version='0.18.1',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'': [
        '*.xml',
        '*.ldif',
        'client/workflow_kickstart.cfg.tmpl',
        'client/.beaker_client/*',
        'labcontroller/install-failure-logs/*',
        'server/kickstarts/*',
        'server/mail-templates/*',
        'server/motd.xml',
        'server/selenium/*.csv',
        'server/selenium/invalid-task_file',
        'server/task-rpms/*'] +
        get_compose_layout()
    },
    namespace_packages=['bkr'],
    install_requires=[
        'bkr.server',
        'bkr.client',
        'selenium',
    ],
)
