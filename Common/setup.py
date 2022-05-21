from setuptools import setup, find_packages

# We don't declare bkr as a namespace package, because we want to actually
# install our bkr/__init__.py file. However, if we don't put the right
# metadata in place during installation, then pkg_resources gets confused and
# prints out an incredibly cryptic warning message if you're developing on
# a system that also has the beaker system package installed.
# (see https://bitbucket.org/pypa/setuptools/issue/2/ for details)
#
# Thus, there is a post-adjustment in "make install" which adds the relevant
# metadata to the installed .egg-info directory for the main beaker package.

setup(
    name='beaker-common',
    version='28.3',
    description='Common components for Beaker packages',
    author='Red Hat, Inc.',
    author_email='beaker-devel@lists.fedorahosted.org',
    url='https://beaker-project.org/',

    packages=find_packages('.'),
    package_dir={'': '.'},
    package_data={'bkr.common': ['schema/*.rnc',
                                 'schema/*.rng',
                                 'schema/*.ttl',
                                 'default.conf']},

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
    ],
)
