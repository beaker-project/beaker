
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software # Foundation, either version 2 of the License, or
# (at your option) any later version.

# Use Python 2 if BKR_PY3 is not defined
ifeq ($(BKR_PY3),)
	BKR_PY3 :=0
endif

COMMAND:= $(shell if [[ $(BKR_PY3) == 0 ]]; then echo "python2"; else echo "python3"; fi)

.PHONY: build
build:
	$(COMMAND) setup.py build
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py for more details
	echo bkr > build/namespace_packages.txt

.PHONY: install
install: build
	$(COMMAND) setup.py install -O1 --skip-build --root $(DESTDIR)
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py for more details
	install -m0644 build/namespace_packages.txt \
	  $(DESTDIR)/usr/lib/python*/site-packages/beaker_common-*.egg-info

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
