# License: GPL v2 or later
# Copyright Red Hat Inc. 2008
ifndef PY_TOPDIR
        PY_TOPDIR = $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
endif

PKGVERSION=$(shell awk 'BEGIN { found = 0 } /Version:/ { if (found == 0) { found = 1; print $$2 } }' $(PY_TOPDIR)/$(PKGNAME).spec)
