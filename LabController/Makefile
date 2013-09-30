# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

.PHONY: build
build:
	python setup.py build

.PHONY: install
install: build
	python setup.py install -O1 --skip-build --root $(DESTDIR)

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build
