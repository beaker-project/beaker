# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from setuptools import setup, find_packages
from time import strftime
import sys
import os
import os.path
import glob
import fnmatch

def glob_(prefix, *patterns):
    if prefix and prefix[-1]!='/':
        prefix += '/'
    answ = []
    for pattern in patterns:
        answ += glob.glob(prefix+pattern)
    answ = list([file for file in answ if not os.path.isdir(file)])
    return answ

def rdglob(prefix, dirs, din=("*"), dex=()):
    """
    Glob directories recursively.
    
    prefix - root directory
    dirs - directory names relative to root to process
    din - include directories matching any of these patterns
    dex - exclude directories matching any of these patterns
    """
    #print "input:", dirs
    if prefix:
        if prefix[-1]!='/':
            prefix += '/'
        dirs = [prefix+dir for dir in dirs]
        #print "prefixed:", dirs
    dirs = list([dir for dir in dirs if os.path.isdir(dir)])
    #print "dirs only:", dirs
    ix = 0
    l = len(prefix)
    def matchf(d):
        d = d[l:]
        for di in din:
            if not fnmatch.fnmatch(d, di):
                return False
        for de in dex:
            if fnmatch.fnmatch(d, de):
                return False
        return True
    while ix < len(dirs):
        dir = dirs[ix]
        ls = [dir+"/"+d for d in os.listdir(dir) if os.path.isdir(dir+"/"+d)]
        #print "ls:", ls
        dirs.extend([d for d in ls if matchf(d)])
        #print "extended:", dirs
        ix += 1
    if prefix:
        dirs = list([dir[l:] for dir in dirs])
    #print "result:", dirs
    return dirs

def glob_to(prefix, new_prefix, dirs):
    if prefix and prefix[-1]!='/':
        prefix += '/'
    return list([(new_prefix+'/'+dir, glob_(prefix, dir+'/*')) for dir in dirs])

# edit MANIFEST.in
prefix = sys.path[0]
if prefix and prefix[-1]!='/':
    prefix += '/'
more_data_files = glob_to(prefix, 'share/beah', rdglob(prefix, [
    'recipes',
    'recipesets',
    'examples/tasks',
    'examples/tests',
    'beah-tests',
    'tests', # FIXME: add some tests here!
    'doc',
    ], dex=('*.tmp', '*.wip')))
#print "more_data_files:", more_data_files

# FIXME: Find out about real requirements - packages, versions.
if os.environ.get('BEAH_NODEP', ''):
    requirements = []
else:
    requirements = ['Twisted_Core >= 0',
            'Twisted_Web >= 0',
            'zope.interface >= 0',
            'simplejson >= 0']

requirements = [] 

setup(

    name="beah",
    version="0.1.a1%s" % os.environ.get('BEAH_DEV', strftime(".dev%Y%m%d%H%M")),

    install_requires=requirements,
    # NOTE: these can be downloaded from pypi:
    #dependency_links=['http://twistedmatrix.com/trac/wiki/Downloads',
    #                      'http://pypi.python.org/pypi/Twisted',
    #                      'http://zope.org/Products/ZopeInterface',
    #                      'http://pypi.python.org/pypi/zope.interface',
    #                      'http://pypi.python.org/pypi/simplejson'],
    # Other requirements: PyXML, python-fpconst, SOAPpy, python-zope-filesystem

    packages=find_packages(),
    py_modules=['beahlib'],
    #package_dir={'':'.'},

    # FIXME: move this to beah.bin(?)
    scripts=['bin/beat_tap_filter'],
    #scripts+=['tests/*'],
    # FIXME: use `grep -R '#!.*python' examples` to find python scripts
    # - this would not work on the well known non-POSIX platform :-/

    namespace_packages=['beah'],

    data_files=[
        ('/etc', ['beah.conf', 'beah_beaker.conf']),
        ('/etc/init.d', ['init.d/beah-srv', 'init.d/beah-fakelc', 'init.d/beah-beaker-backend', 'init.d/beah-fwd-backend']),
        ] + more_data_files,
    #package_data={
    #    '': ['beah.conf', 'beah_beaker.conf'],
    #    'init.d': ['beah-srv', 'beah-beaker-backend'],
    #},

    entry_points={
        'console_scripts': (
            'beah-srv = beah.bin.srv:main',
            'beah = beah.bin.cli:main',
            'beah-cmd-backend = beah.bin.cmd_backend:main',
            'beah-out-backend = beah.bin.out_backend:main',
            'beah-beaker-backend = beah.backends.beakerlc:main',
            'beah-fwd-backend = beah.backends.forwarder:main',
            'beah-fakelc = beah.tools.fakelc:main',
            'beah-rhts-task = beah.tasks.rhts_xmlrpc:main',
            'beah-root = beah.tools:main_root',
            'beah-data-root = beah.tools:mina_data_root',
            'beah-data-file = beah.tools:main_data_file',
            'beah-data-dir = beah.tools:main_data_dir',
        ),
    },

    license="GPL",
    keywords="test testing harness beaker twisted qa",
    url="http://fedorahosted.org/beaker/wiki",
    author="Marian Csontos",
    author_email="mcsontos@redhat.com",
    description="Beah - Beaker Test Harness. Part of Beaker project - http://fedorahosted.org/beaker/wiki.",
    long_description="""\
Beah - Beaker Test Harness.

Ultimate Test Harness, with goal to serve any tests and any test scheduler
tools. Harness consist of a server and two kinds of clients - backends and
tasks.

Backends issue commands to Server and process events from tasks.
Tasks are mostly events producers.

Powered by Twisted.
""",
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Twisted',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: POSIX :: Linux', # FIXME: Wishing 'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Testing',
    ],
)

