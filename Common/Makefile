# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

include ../rpmspec_rules.mk
include ../py_rules.mk

build:	bkr/common/__init__.py py-build
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py.in for more details
	echo bkr > build/namespace_packages.txt

bkr/common/__init__.py: bkr/common/__init__.py.in
	sed -e 's/@VERSION@/$(PKGVERSION)/g' < $< > $@

install: build py-install
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py.in for more details
	install -m0644 build/namespace_packages.txt \
	  $(DESTDIR)/usr/lib/python*/site-packages/bkr-*.egg-info

clean:	py-clean
	rm bkr/common/__init__.py
