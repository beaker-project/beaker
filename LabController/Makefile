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
	$(INSTALL) conf.d/beaker-lab-controller.conf $(DESTDIR)/etc/httpd/conf.d/beaker-lab-controller.conf
	$(INSTALL_EXEC) cron.hourly/beaker_expire_distros $(DESTDIR)/etc/cron.hourly/beaker_expire_distros
	mkdir -p $(DESTDIR)/var/run/beaker-lab-controller
	install -D -m755 addDistro/addDistro.sh $(DESTDIR)/var/lib/beaker/addDistro.sh
	for addDistro in $(ADDDISTROD); do \
		install -D -m755 addDistro/$$addDistro $(DESTDIR)/var/lib/beaker/$$addDistro;\
	done

clean:
	for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done
