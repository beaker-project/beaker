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
    name='beaker-integration-tests',
    version='28.3',
    description='Integration tests for Beaker',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'': [
        '*.xml',
        '*.ldif',
        'client/workflow_kickstart.cfg.tmpl',
        'client/.beaker_client/*',
        'labcontroller/watchdog-script-test.sh',
        'labcontroller/install-failure-logs/*',
        'labcontroller/pxemenu-templates/*',
        'server/*.sql',
        'server/database-dumps/*.sql',
        'server/kickstarts/*',
        'server/mail-templates/*',
        'server/selenium/*.csv',
        'server/selenium/invalid-task_file',
        'server/task-rpms/*'] +
        get_compose_layout()
    },
    data_files=[
        ('beaker-integration-tests', ['motd.xml']),
    ],
    namespace_packages=['bkr'],
    install_requires=[
        'beaker-server',
        'beaker-client',
        'selenium',
    ],
)
