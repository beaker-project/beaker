# License: GPL v2 or later
# Copyright Red Hat Inc. 2009

PKGNAME=beaker

SCM_REMOTEREPO_RE = ^ssh://(.*@)?git.fedorahosted.org/git/$(PKGNAME).git$
UPLOAD_URL = ssh://fedorahosted.org/$(PKGNAME)

SUBDIRS := Common Client
ifdef WITH_SERVER
    SUBDIRS += Server
endif
ifdef WITH_LABCONTROLLER
    SUBDIRS += LabController
endif
ifdef WITH_INTTESTS
    SUBDIRS += IntegrationTests
endif

build:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i build; done

include rpmspec_rules.mk
include git_rules.mk
include upload_rules.mk

install:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i install; done

clean:
	-rm -rf rpm-build
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done

srpm: clean $(PKGNAME)-$(PKGVERSION).tar.bz2
	mkdir -p rpm-build
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	$(RPMBUILDOPTS) -ts $(PKGNAME)-$(PKGVERSION).tar.bz2

rpm: clean $(PKGNAME)-$(PKGVERSION).tar.bz2
	mkdir -p rpm-build
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	$(RPMBUILDOPTS) -tb $(PKGNAME)-$(PKGVERSION).tar.bz2

rpms: rpm
