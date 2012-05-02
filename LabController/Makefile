INSTALL = install -D -m644
INSTALL_EXEC = install -D -m755
ADDDISTROD = $(shell cd addDistro; ls addDistro.d/*)

SUBDIRS := proxy

build:
	for i in $(SUBDIRS); do $(MAKE) -C $$i; done

install:
	for i in $(SUBDIRS); do $(MAKE) -C $$i install; done
	$(INSTALL) aux/anamon $(DESTDIR)/var/www/beaker/anamon
	$(INSTALL) aux/anamon.init $(DESTDIR)/var/www/beaker/anamon.init
	$(INSTALL) aux/koan.init $(DESTDIR)/var/www/beaker/koan.init
	$(INSTALL) conf.d/beaker-lab-controller.conf $(DESTDIR)/etc/httpd/conf.d/beaker-lab-controller.conf
	$(INSTALL_EXEC) cron.hourly/cobbler_expire_distros $(DESTDIR)/etc/cron.hourly/cobbler_expire_distros
	$(INSTALL_EXEC) cron.daily/beaker_expire_osversion $(DESTDIR)/etc/cron.daily/beaker_expire_osversion
	$(INSTALL_EXEC) triggers/sync/post/osversion.trigger $(DESTDIR)/var/lib/cobbler/triggers/sync/post/osversion.trigger
	mkdir -p $(DESTDIR)/var/run/beaker-lab-controller
	install -D -m755 addDistro/addDistro.sh $(DESTDIR)/var/lib/beaker/addDistro.sh
	for addDistro in $(ADDDISTROD); do \
		install -D -m755 addDistro/$$addDistro $(DESTDIR)/var/lib/beaker/$$addDistro;\
	done
	mkdir -p $(DESTDIR)/var/lib/beaker/osversion_data

clean:
	for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done
