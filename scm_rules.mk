# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

ifndef SCM_REMOTE_BRANCH
	SCM_REMOTE_BRANCH = dummy
endif

ifndef SCM_LOCAL_BRANCH
	SCM_LOCAL_BRANCH = $(SCM_REMOTE_BRANCH)
endif

ifndef SCM_ACTUAL_REMOTE_BRANCH
	SCM_ACTUAL_REMOTE_BRANCH = $(SCM_REMOTE_BRANCH)
endif

ifndef SCM_TAG
	SCM_TAG = $(PKGNAME)-$(subst .,_,$(PKGVERSION))
endif

ifndef FORCETAG
	SCM_FORCE_FLAG =
else
	SCM_FORCE_FLAG = -f
endif

ifndef SCM_CHANGED_FILES_SINCE_TAG_COMMAND
	SCM_CHANGED_FILES_SINCE_TAG_COMMAND = $(SCM_DIFF_TAG_COMMAND) | egrep '^---|^\+\+\+' | sed 's:^...[   ][      ]*[ab]/::g' | sort -u
endif

checkmods:
	@if $(SCM_CHECK_MODS); then \
		echo There are modifications not yet committed. Commit these first. >&2; \
		exit 1; \
	fi

checkrepo:
ifndef BYPASSUPSTREAM
	@x=0; \
	if [ -z "$$(echo $(SCM_REMOTEREPO) | egrep -x '$(SCM_REMOTEREPO_RE)')" ]; then \
		echo The repository $(SCM_REMOTEREPO) is not the upstream of $(PKGNAME). >&2; \
		x=1; \
	fi; if [ "$(SCM_REMOTE_BRANCH)" != "$(SCM_ACTUAL_REMOTE_BRANCH)" ]; then \
		echo The remote branch must be $(SCM_REMOTE_BRANCH), not $(SCM_ACTUAL_REMOTE_BRANCH) >&2; \
		x=1; \
	fi; if [ "$$x" -ne 0 ]; then \
		echo Pushing to anywhere else may not be helpful when creating an archive. >&2; \
		echo Use BYPASSUPSTREAM=1 to not access upstream or FORCEPUSH=1 to push anyway. >&2; \
		exit 1; \
	fi
endif

incoming: checkrepo
	@if $(SCM_CHECK_INCOMING_CHANGES); then \
		echo There are incoming changes which need to be integrated. >&2; \
		echo Pull them with "$(SCM_PULL_COMMAND)" and resolve possible conflicts. >&2; \
		exit 1; \
	fi

tag:
ifndef FORCETAG
	@if $(SCM_CHECK_TAG); then \
		echo "Tag $(SCM_TAG) exists already. Use FORCETAG=1 to force tagging." >&2 ; \
		exit 1; \
	fi
endif
	@if [ -n "$(FORCETAG)" ]; then \
		tagcmd="$(SCM_FORCE_TAG_COMMAND)"; \
	else \
		tagcmd="$(SCM_TAG_COMMAND)"; \
	fi; \
	if [ -n "$(SCM_LAST_TAG)" -a -z "$$($(SCM_DIFF_LAST_TAG_COMMAND))" ]; then \
		echo "No differences to last tagged release '$(SCM_LAST_TAG)'. Not tagging."; \
	else \
		echo "Tagging '$(SCM_TAG)'."; \
		$(SCM_TAG_COMMAND); \
	fi

ifdef FORCEPUSH
archivepush:
else
archivepush: checkrepo
endif
ifndef BYPASSUPSTREAM
	@echo Pushing to repository $(SCM_REMOTEREPO).
	@if ! $(SCM_PUSH_REMOTE_COMMAND); then \
		echo Pushing failed. >&2; \
		echo Use BYPASSUPSTREAM=1 to bypass pushing. >&2; \
		exit 1; \
	fi
endif

archive: checkmods incoming tag archivepush
ifndef FORCEARCHIVE
	@if [ -e "${PKGNAME}-$(PKGVERSION).tar.bz2" ]; then \
		echo "File ${PKGNAME}-$(PKGVERSION).tar.bz2 exists already." >&2; \
		echo "Use FORCEARCHIVE=1 to force overwriting it." >&2; \
		exit 1; \
	fi
endif
	@$(SCM_ARCHIVE_COMMAND)
	@echo "The archive is in ${PKGNAME}-$(PKGVERSION).tar.bz2"

snaparchive:
	@$(SCM_SNAP_ARCHIVE_COMMAND)
	@echo "The _local_ snapshot archive is in ${PKGNAME}-$(PKGVERSION).tar.bz2"

dif:	diff

diff:
	@echo Differences to tag $(SCM_TAG):
	@echo
	@$(SCM_DIFF_TAG_COMMAND)

sdif:	shortdiff

shortdiff:
	@echo Files changed since tag $(SCM_TAG):
	@echo
	@$(SCM_CHANGED_FILES_SINCE_TAG_COMMAND)

llog:	lastlog

lastlog:
	@echo Log since tag $(SCM_TAG)
	@echo
	@$(SCM_LASTLOG_COMMAND)
