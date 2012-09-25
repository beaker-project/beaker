# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

.PHONY: all
all:	build

include ../rpmspec_rules.mk
include ../py_rules.mk

.PHONY: build
build: $(_SETUP_PY)
	env PYTHONPATH=../Common:src:$${PYTHONPATH:+:$$PYTHONPATH} \
	    python $(SETUP_PY) build \
	    | tee build.out
	@if grep -q ImportError build.out ; then \
	    echo "ImportErrors in build output, did Sphinx autodoc fail?" ; \
	    exit 1 ; \
	fi

install:	py-install
	ln -s bkr-distro-trees-verify.1.gz $(DESTDIR)/usr/share/man/man1/bkr-distros-verify.1.gz

clean:	py-clean
