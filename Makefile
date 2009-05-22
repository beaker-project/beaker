# License: GPL v2 or later
# Copyright Red Hat Inc. 2009

PKGNAME=beaker

SCM_REMOTEREPO_RE = ^ssh://(.*@)?git.fedorahosted.org/git/$(PKGNAME).git$
UPLOAD_URL = ssh://fedorahosted.org/$(PKGNAME)

SUBDIRS := Client LabController Server beakerlib

build:
	for i in $(SUBDIRS); do $(MAKE) -C $$i; done

include rpmspec_rules.mk
include git_rules.mk
include upload_rules.mk

install:
	for i in $(SUBDIRS); do $(MAKE) -C $$i install; done

clean:
	for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done

srpm: $(PKGNAME)-$(PKGVERSION).tar.bz2
	rpmbuild $(RPMBUILDOPTS) -ts $<

rpm: $(PKGNAME)-$(PKGVERSION).tar.bz2
	rpmbuild $(RPMBUILDOPTS) -tb $<

rpms: rpm
