
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software # Foundation, either version 2 of the License, or
# (at your option) any later version.

# Python 2 default
BKR_PY3 ?= 0
DEPCMD := yum-builddep
SUBDIRS := Common Client documentation Server LabController IntegrationTests

ifeq ($(BKR_PY3),1)
	DEPCMD := dnf builddep
	SUBDIRS := Common Client documentation LabController
endif


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
