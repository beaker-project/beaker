
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software # Foundation, either version 2 of the License, or
# (at your option) any later version.

# Python 2 default
ifeq ($(BKR_PY3),)
	BKR_PY3 :=0
endif

DEPCMD  :=  $(shell if [ -f /usr/bin/dnf ]; then echo "dnf builddep"; else echo "yum-builddep"; fi)
SUBDIRS :=  $(shell if [[ $(BKR_PY3) == 0 ]]; then echo "Common Client documentation Server LabController IntegrationTests"; else echo "Common Client documentation"; fi)


.PHONY: build
build:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i build; done

.PHONY: install
install:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i install; done

.PHONY: clean
clean:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i clean; done

check:
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i check; done

.PHONY: devel
devel: build
	set -e; for i in $(SUBDIRS); do $(MAKE) -C $$i devel; done

deps:
	sudo $(DEPCMD) -y beaker.spec

submods:
	git submodules init
	git submodules update
