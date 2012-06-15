# Copyright (c) 2012 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Dan Callaghan <dcallagh@redhat.com>

TOPLEVEL_NAMESPACE=distribution
PACKAGE_NAME=beaker
RELATIVE_PATH=fake_systems
export TESTVERSION=1.0
export TEST=/$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)

# executables to be built should be added here, they will be generated on the system under test.
BUILT_FILES= 

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh Makefile PURPOSE hosts.sh system-csv.sh power-csv.sh \
    dummy_fast dummy_medium dummy_slow dummy_flakey

.PHONY: run
run: $(FILES) build
	./runtest.sh

.PHONY: build
build: $(BUILT_FILES)

.PHONY: clean
clean:
	rm -f *~ *.rpm $(BUILT_FILES)

# Include Common Makefile
include /usr/share/rhts/lib/rhts-make.include

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:        Dan Callaghan <dcallagh@redhat.com>" > $(METADATA)
	@echo "Name:         $(TEST)" >> $(METADATA)
	@echo "Path:         $(TEST_DIR)" >> $(METADATA)
	@echo "License:      GPL-2" >> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)" >> $(METADATA)
	@echo "Description:  Adds fake systems to Beaker" >> $(METADATA)
	@echo "TestTime:     10m" >> $(METADATA)
	@echo "Requires:     beakerlib" >> $(METADATA)
	@echo "Requires:     curl" >> $(METADATA)
	@echo "Requires:     python-daemon" >> $(METADATA)
	@echo "Requires:     python-lxml" >> $(METADATA)
	@echo "Requires:     python-gevent" >> $(METADATA)

	rhts-lint $(METADATA)
