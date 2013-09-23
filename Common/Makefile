# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

.PHONY: build
build:
	python setup.py build
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py for more details
	echo bkr > build/namespace_packages.txt

.PHONY: install
install: build
	python setup.py install -O1 --skip-build --root $(DESTDIR)
	# Workaround for https://bitbucket.org/pypa/setuptools/issue/2/
	# See adjacent setup.py for more details
	install -m0644 build/namespace_packages.txt \
	  $(DESTDIR)/usr/lib/python*/site-packages/bkr-*.egg-info

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build
