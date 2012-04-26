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

# The toplevel namespace within which the test lives.
TOPLEVEL_NAMESPACE=distribution

# The name of the package under test:
PACKAGE_NAME=beaker

# The path of the test below the package:
RELATIVE_PATH=custom_kickstart

# Version of the Test. Used with make tag.
export TESTVERSION=1.0

# The combined namespace of the test.
export TEST=/$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)

.PHONY: all install build download clean

# executables to be built should be added here, they will be generated on the system under test.
BUILT_FILES=

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh Makefile PURPOSE \
	test_custom_kickstart.sh \
	test_no_custom_kickstart.sh

run: $(FILES) build
	./runtest.sh

build: $(BUILT_FILES)

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
	@echo "License:      GPLv2" >> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)" >> $(METADATA)
	@echo "Description:  test Beaker jobs with custom kickstart" >> $(METADATA)
	@echo "TestTime:     1h" >> $(METADATA)
	@echo "RunFor:       $(PACKAGE_NAME)" >> $(METADATA)
	@echo "Requires:     $(PACKAGE_NAME)-client" >> $(METADATA)

	rhts-lint $(METADATA)
