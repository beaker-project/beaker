
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

.PHONY: build
build:
	python2 setup.py build

.PHONY: install
install: build
	python2 setup.py install -O1 --skip-build \
	    --install-data=/usr/share --root $(DESTDIR)

.PHONY: clean
clean:
	python2 setup.py clean
	rm -rf build

.PHONY: check
check:
	# This package contains only integration tests, no unit tests.
