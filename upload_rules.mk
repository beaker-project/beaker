# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

ifdef UPLOAD_URL
upload:
	@url="$(UPLOAD_URL)"; \
	case "$$url" in \
	ssh://*) \
		url="$${url#ssh://}"; \
		userhostname="$${url%%/*}"; \
		path="$${url#*/}"; \
		echo Copying "$(PKGNAME)-$(PKGVERSION).tar.bz2" to "$$userhostname:$$path"; \
		scp "$(PKGNAME)-$(PKGVERSION).tar.bz2" "$$userhostname:$$path"; \
		;; \
	*) \
		echo Unknown method. >&2; \
		exit 1; \
		;; \
	esac
endif
