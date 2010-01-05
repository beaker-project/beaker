# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

include ../rpmspec_rules.mk
include ../py_rules.mk

build:	beaker/__init__.py py-build

beaker/__init__.py: beaker/__init__.py.in
	sed -e 's/@VERSION@/$(PKGVERSION)/g' < $< > $@

install: build py-install

clean:	py-clean
