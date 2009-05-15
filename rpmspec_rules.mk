# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

PKGVERSION=$(shell awk 'BEGIN { found = 0 } /Version:/ { if (found == 0) { found = 1; print $$2 } }' $(PKGNAME).spec)
