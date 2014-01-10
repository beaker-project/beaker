# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

.PHONY: build
build:
	env PYTHONPATH=../Common:src:$${PYTHONPATH:+:$$PYTHONPATH} \
	    python setup.py build

.PHONY: install
install:
	python setup.py install -O1 --skip-build --root $(DESTDIR)

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build
