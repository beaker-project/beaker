from setuptools import setup, find_packages
from time import strftime
import os
setup(
    name               = "beah",
    version            = "0.1.a1%s" % os.environ.get('BEAH_DEV',
                                strftime(".dev%Y%m%d%H%M")),
    # FIXME: Find out about real requirements.
    install_requires   = ['Twisted>=0',
                          'zope.interface>=0',
                          'simplejson>=0'],
    # NOTE: these can be downloaded from pypi:
    # Other requirements: PyXML, python-fpconst, SOAPpy, python-zope-filesystem
    #dependency_links   = ['http://twistedmatrix.com/trac/wiki/Downloads',
    #                      'http://pypi.python.org/pypi/Twisted',
    #                      'http://zope.org/Products/ZopeInterface',
    #                      'http://pypi.python.org/pypi/zope.interface',
    #                      'http://pypi.python.org/pypi/simplejson'],

    packages           = find_packages(),
    #package_dir        = {'':'.'},

    # FIXME: move this to beah.bin(?)
    #scripts            = ['bin/beat_tap_filter']

    namespace_packages = ['beah'],

    #data_files = [('/etc/beah/', ['server.conf']),],
    #package_data = {
    #    '/etc/beah': ['server.conf'],
    #},

    entry_points       = {
        'console_scripts': (
            'beah-srv = beah.bin.srv:main',
            'beah-cmd-backend = beah.bin.cmd_backend:main',
            'beah-out-backend = beah.bin.out_backend:main',
            'beah = beah.bin.cli:main',
        ),
    },

    license            = "GPL",
    keywords           = "test testing harness beaker twisted qa",
    url                = "http://fedorahosted.org/beaker/wiki",
    author             = "Marian Csontos",
    author_email       = "mcsontos@redhat.com",
    #maintainer         = "Marian Csontos",
    #maintainer_email   = "mcsontos@redhat.com",
    description        = "Beah - Beaker Test Harness. Part of Beaker project - http://fedorahosted.org/beaker/wiki.",
    long_description   = """\
Beah - Beaker Test Harness.

Ultimate Test Harness, with goal to serve any tests and any test scheduler
tools. Harness consist of a server and two kinds of clients - backends and
tasks.

Backends issue commands to Server and process events from tasks.
Tasks are mostly events producers.

Powered by Twisted.
"""
)

