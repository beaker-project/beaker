
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

BKR_PY3 ?= 0
COMMAND := python2

ifeq ($(BKR_PY3),1)
	COMMAND := python3
endif


.PHONY: build
build:
	$(COMMAND) setup.py build

.PHONY: install
install: build
	$(COMMAND) setup.py install -O1 --skip-build --root $(DESTDIR)

.PHONY: clean
clean:
	$(COMMAND) setup.py clean
	rm -rf build

.PHONY: check
check:
	./run-tests.sh

.PHONY: devel
devel:
	DESTDIR="/" make install
