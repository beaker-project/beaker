SNIPPETS = $(shell ls snippets/*)
KICKSTARTS = $(shell ls kickstarts/*)
INSTALL = install -D -m644

all:
	@echo "Nothing to build"

install:
	$(INSTALL) aux/rhts-checkin $(DESTDIR)/var/www/beaker/rhts-checkin
	$(INSTALL) conf.d/beaker-lab-controller.conf $(DESTDIR)/etc/httpd/conf.d/beaker-lab-controller.conf
	$(INSTALL) cron.daily/expire_distros $(DESTDIR)/etc/cron.daily/expire_distros
	$(INSTALL) triggers/sync/post/osversion.trigger $(DESTDIR)/var/lib/cobbler/triggers/sync/post/osversion.trigger
	$(INSTALL) triggers/install/pre/clear_console_log.trigger $(DESTDIR)/var/lib/cobbler/triggers/install/pre/clear_console_log.trigger
	for snippet in $(SNIPPETS); do \
		$(INSTALL) $$snippet $(DESTDIR)/var/lib/cobbler/$$snippet;\
	done
	for kickstart in $(KICKSTARTS); do \
		$(INSTALL) $$kickstart $(DESTDIR)/var/lib/cobbler/$$kickstart;\
	done
