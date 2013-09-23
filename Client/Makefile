# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

.PHONY: build
build:
	env PYTHONPATH=../Common:src:$${PYTHONPATH:+:$$PYTHONPATH} \
	    python setup.py build \
	    | tee build.out
	@if grep -q ImportError build.out ; then \
	    echo "ImportErrors in build output, did Sphinx autodoc fail?" ; \
	    exit 1 ; \
	fi

.PHONY: install
install:
	python setup.py install -O1 --skip-build --root $(DESTDIR)

.PHONY: clean
clean:
	python setup.py clean
	rm -rf build
