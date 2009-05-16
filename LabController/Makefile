SNIPPETS = $(shell ls snippets/*)
KICKSTARTS = $(shell ls kickstarts/*)
INSTALL = install -D -m644
INSTALL_EXEC = install -D -m755

all:
	@echo "Nothing to build"

install:
	$(INSTALL) aux/rhts-checkin $(DESTDIR)/var/www/beaker/rhts-checkin
	$(INSTALL) conf.d/beaker-lab-controller.conf $(DESTDIR)/etc/httpd/conf.d/beaker-lab-controller.conf
	$(INSTALL_EXEC) cron.daily/expire_distros $(DESTDIR)/etc/cron.daily/expire_distros
	$(INSTALL_EXEC) triggers/sync/post/osversion.trigger $(DESTDIR)/var/lib/cobbler/triggers/sync/post/osversion.trigger
	$(INSTALL_EXEC) triggers/install/pre/clear_console_log.trigger $(DESTDIR)/var/lib/cobbler/triggers/install/pre/clear_console_log.trigger
	for snippet in $(SNIPPETS); do \
		$(INSTALL) $$snippet $(DESTDIR)/var/lib/cobbler/$$snippet;\
	done
	for kickstart in $(KICKSTARTS); do \
		$(INSTALL) $$kickstart $(DESTDIR)/var/lib/cobbler/$$kickstart;\
	done
