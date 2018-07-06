# License: GPL v2 or later
# Copyright Red Hat Inc. 2008

INITSYS :=  $(shell if [ -f /usr/bin/systemctl ]; then echo "systemd"; else echo "sysvinit"; fi)

.PHONY: build
build:
	env PYTHONPATH=../Common$${PYTHONPATH:+:$$PYTHONPATH} \
	    python2 setup.py build --install-data=/usr/share/

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
	./run-tests.sh

.PHONY: devel
devel:
	-if [[ $(INITSYS) == "systemd" ]] ; then \
		systemctl stop beakerd; \
	else \
		service beakerd stop; \
	fi
	DESTDIR="/" make install
	if [[ $(INITSYS) == "systemd" ]] ; then \
		systemctl daemon-reload; \
		systemctl restart beakerd; \
	else \
		service beakerd restart; \
	fi

assets/favicon.ico: assets/favicon-16.png assets/favicon-32.png assets/favicon-64.png
	icotool -c -o $@ $^

assets/favicon-%.png: assets/favicon.svg
	inkscape -z -e $@ -w $* -h $* $<
	optipng $@
