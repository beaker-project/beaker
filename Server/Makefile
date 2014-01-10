# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

.PHONY: build
build:
	env PYTHONPATH=../Common$${PYTHONPATH:+:$$PYTHONPATH} \
	    python setup.py build --install-data=/usr/share/

.PHONY: install
install: build
	python setup.py install -O1 --skip-build \
            --install-data=/usr/share --root $(DESTDIR)

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build
