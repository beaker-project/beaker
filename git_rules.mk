# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

ifndef SCM_BRANCH
	SCM_REMOTE_BRANCH = master
endif
ifndef SCM_LOCAL_BRANCH
	SCM_LOCAL_BRANCH = $(SCM_REMOTE_BRANCH)
endif

SCM_ACTUAL_REMOTE_BRANCH = $(notdir $(shell git config branch.$(SCM_LOCAL_BRANCH).merge))

SCM_REMOTEREPO_NICKNAME = $(shell git config branch.$(SCM_LOCAL_BRANCH).remote)
SCM_REMOTEREPO = $(shell git config remote.$(SCM_REMOTEREPO_NICKNAME).url)

SCM_CHECK_INCOMING_CHANGES = [ -n "$$(git fetch >&/dev/null && git log ..$(SCM_REMOTEREPO_NICKNAME)/$(SCM_REMOTE_BRANCH))" ]
SCM_CHECK_MODS = [ -n "$$(git diff)" -o -n "$$(git diff -a)" ]
SCM_CHECK_TAG = [ -n "$$(git tag -l $(SCM_TAG))" ]

SCM_PULL_COMMAND = git pull
SCM_TAG_COMMAND = git tag $(SCM_FORCE_FLAG) $(SCM_TAG)
SCM_LAST_TAG_REV = $(shell git rev-list --no-walk -n1 $$(git tag))
SCM_LAST_TAG = $(shell git tag | while read tag; do if [ "$$(git rev-parse $$tag)" = "$(SCM_LAST_TAG_REV)" ]; then echo "$$tag"; break; fi; done)
SCM_DIFF_TAG_COMMAND = git diff $(SCM_TAG)
SCM_DIFF_LAST_TAG_COMMAND = git diff $(SCM_LAST_TAG)
SCM_PUSH_REMOTE_COMMAND = { git push --all $(SCM_REMOTEREPO) && git push --tags $(SCM_REMOTEREPO); }
SCM_SNAP_ARCHIVE_COMMAND = git archive --format=tar --prefix=$(PKGNAME)-$(PKGVERSION)/ HEAD | bzip2 -9 > $(PKGNAME)-$(PKGVERSION).tar.bz2
SCM_ARCHIVE_COMMAND = git archive --format=tar --prefix=$(PKGNAME)-$(PKGVERSION)/ $(SCM_TAG) | bzip2 -9 > $(PKGNAME)-$(PKGVERSION).tar.bz2
SCM_LASTLOG_COMMAND = git log $(SCM_TAG)..

include scm_rules.mk
