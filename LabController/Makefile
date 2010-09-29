SNIPPETS = $(shell ls snippets/*)
KICKSTARTS = $(shell ls kickstarts/*)
INSTALL = install -D -m644
INSTALL_EXEC = install -D -m755

SUBDIRS := proxy

build:
	for i in $(SUBDIRS); do $(MAKE) -C $$i; done

install:
	for i in $(SUBDIRS); do $(MAKE) -C $$i install; done
	$(INSTALL) aux/rhts-checkin $(DESTDIR)/var/www/beaker/rhts-checkin
	$(INSTALL) aux/koan.init $(DESTDIR)/var/www/beaker/koan.init
	$(INSTALL) conf.d/beaker-lab-controller.conf $(DESTDIR)/etc/httpd/conf.d/beaker-lab-controller.conf
	$(INSTALL_EXEC) cron.daily/expire_distros $(DESTDIR)/etc/cron.daily/expire_distros
	$(INSTALL_EXEC) triggers/sync/post/osversion.trigger $(DESTDIR)/var/lib/cobbler/triggers/sync/post/osversion.trigger
	for snippet in $(SNIPPETS); do \
		$(INSTALL) $$snippet $(DESTDIR)/var/lib/cobbler/$$snippet;\
	done
	mkdir -p $(DESTDIR)/var/lib/cobbler/snippets/per_system/ks_appends
	mkdir -p $(DESTDIR)/var/run/beaker-lab-controller
	for kickstart in $(KICKSTARTS); do \
		$(INSTALL) $$kickstart $(DESTDIR)/var/lib/cobbler/$$kickstart;\
	done

clean:
	for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done
