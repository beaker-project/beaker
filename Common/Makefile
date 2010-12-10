# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

include ../rpmspec_rules.mk
include ../py_rules.mk

build:	bkr/__init__.py py-build

bkr/__init__.py: bkr/__init__.py.in
	sed -e 's/@VERSION@/$(PKGVERSION)/g' < $< > $@

install: build py-install

clean:	py-clean
	rm bkr/__init__.py
