# $Id: $
PKGNAME=$(shell python setup.py --name)
VERSION=$(shell python setup.py --version)
RPMBUILDOPTS=--define "_topdir ${PWD}/dist" --define "_specdir %{_topdir}" --define "_sourcedir %{_topdir}" --define "_srcrpmdir %{_topdir}" --define "_rpmdir %{_topdir}" --define "_builddir %{_topdir}" --define "_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm"

default: all

all:
	@echo "Nothing to do"

docs:
	epydoc -n medusa -o docs/epydoc -u https://fedorahosted.org/beaker \
		`find medusa -name '*.py'`

test:
	nosetests

todo:
	grep -r --color=auto TODO medusa/ || :
	grep -r --color=auto FIXME medusa/ || :

clean:
	find . -name '*.pyc' | xargs rm -f
	rm -rf medusa-* medusa.egg-info
	rm -rf dist build rpm-build

dist:
	python setup.py sdist --formats=bztar

build:
	python setup.py build

install:
	python setup.py install -f -O1 --skip-build

shell:
	tg-admin --config=medusa.cfg shell

srpm: dist
	rpmbuild $(RPMBUILDOPTS) -ts dist/${PKGNAME}-${VERSION}.tar.bz2

pyflakes:
	find . -name '*.py' | xargs pyflakes

init:
	tg-admin --config=medusa.cfg sql create && medusa/tools/init.py && medusa/tools/dev_init.py && medusa/tools/pickledb.py load medusa-pickledb*

run:
	python start-medusa.py

install-deps:
	su -c "yum install TurboGears python-TurboMail python-fedora python-sqlalchemy koji mash yum-utils git intltool python-bugzilla python-genshi \
python-crypto python-imaging python-turboflot python-tgcaptcha python-nose.noarch"

rpms: rpm

rpm: dist
	rpmbuild $(RPMBUILDOPTS) -tb dist/${PKGNAME}-${VERSION}.tar.bz2

.PHONY: docs test todo clean dist build install srpm pyflakes shell init run install-deps
