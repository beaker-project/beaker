PACKAGE_ROOT= ~/projects/beaker/packages/

PYTHONV=2.6
PYTHON_VER=2.6.2
ZOPEIF_VER=3.3.0
TWISTED_VER=8.2.0
SIMPLEJSON_VER=2.0.9
SETUPTOOLS_VER=0.6c9
BEAH_VER=0.1a1

mkdir -p $PACKAGE_ROOT
cd $PACKAGE_ROOT

mkdir BUILD RPMS SOURCES SPECS SRPMS

cd SOURCES
wget http://pypi.python.org/packages/source/s/setuptools/setuptools-${SETUPTOOLS_VER}.tar.gz
wget http://www.python.org/ftp/python/${PYTHON_VER}/Python-${PYTHON_VER}.tar.bz2
wget http://www.zope.org/Products/ZopeInterface/${ZOPEIF_VER}/zope.interface-${ZOPEIF_VER}.tar.gz
wget http://tmrc.mit.edu/mirror/twisted/Twisted/8.2/Twisted-${TWISTED_VER}.tar.bz2
wget http://pypi.python.org/packages/source/s/simplejson/simplejson-${SIMPLEJSON_VER}.tar.gz
git archive --format=tar --prefix=beah-${BEAH_VER} http://git.fedorahosted.org/git/beaker.git master Harness | gzip > beah-${BEAH_VER}.tar.gz
cd ..

PYBIN_NAME=python${PYTHONV}

cd SPECS
cp $HARNESS_ROOT/*.spec .

rpmbuild -ba beah.spec
