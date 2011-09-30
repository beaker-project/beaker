# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGNAME=beaker

all: build
	
include ../rpmspec_rules.mk
include ../py_rules.mk

build: $(_SETUP_PY)
	env PYTHONPATH=../Common$${PYTHONPATH:+:$$PYTHONPATH} \
	    python $(SETUP_PY) build --install-data=/usr/share/ \
	    | tee build.out
	@if grep -q ImportError build.out ; then \
	    echo "ImportErrors in build output, did Sphinx autodoc fail?" ; \
	    exit 1 ; \
	fi

install: $(_SETUP_PY)
	python $(SETUP_PY) install -O1 --skip-build \
            --install-data=/usr/share --root $(DESTDIR)

clean: py-clean
