
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software # Foundation, either version 2 of the License, or
# (at your option) any later version.

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

.PHONY: check
check:
	./run-tests.sh
	env PYTHONPATH=.${PYTHONPATH:+:$PYTHONPATH} \
	    pylint --disable=W --report=no --rcfile=../Misc/pylint-errors.cfg \
	    bkr