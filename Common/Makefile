# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

include ../rpmspec_rules.mk
include ../py_rules.mk

beaker/__init__.py: beaker/__init__.py.in
	sed -e 's/@VERSION@/$(PKGVERSION)/g' < $< > $@

build:	beaker/__init__.py py-build

install: beaker/__init__.py py-install

clean:	py-clean
