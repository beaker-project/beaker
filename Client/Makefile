# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

.PHONY: all
all:	build

include ../rpmspec_rules.mk
include ../py_rules.mk

.PHONY: build
build: $(_SETUP_PY)
	env PYTHONPATH=../Common$${PYTHONPATH:+:$$PYTHONPATH} \
	    python $(SETUP_PY) build

install:	py-install

clean:	py-clean
