# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
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
# Author: Bill Peck

# The toplevel namespace within which the test lives.
# FIXME: You will need to change this:
TOPLEVEL_NAMESPACE=distribution

# The name of the package under test:
# FIXME: you wil need to change this:
PACKAGE_NAME=

# The path of the test below the package:
# FIXME: you wil need to change this:
RELATIVE_PATH=inventory

# Version of the Test. Used with make tag.
export TESTVERSION=1.2

# The combined namespace of the test.
export TEST=/$(TOPLEVEL_NAMESPACE)/$(RELATIVE_PATH)


# A phony target is one that is not really the name of a file.
# It is just a name for some commands to be executed when you
# make an explicit request. There are two reasons to use a
# phony target: to avoid a conflict with a file of the same
# name, and to improve performance.
.PHONY: all install download clean

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh Makefile PURPOSE

run: $(FILES) build
	./runtest.sh

build:
	chmod a+x ./runtest.sh

clean: $(TARGET)-clean
	rm -f *~ *.rpm

# Include Common Makefile
include /usr/share/rhts/lib/rhts-make.include

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
# Change to the test owner's name
	@echo "Owner:        Beaker Developers <beaker-devel@lists.fedorahosted.org>" > $(METADATA)
	@echo "Name:         $(TEST)" >> $(METADATA)
	@echo "Path:         $(TEST_DIR)"	>> $(METADATA)
	@echo "License:      GPL" >> $(METADATA)
	@echo "Releases:     RHELServer5 RHEL6" >> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)"	>> $(METADATA)
	@echo "Description:  This refreshes the database with the hardware inventory of the machine its run on">> $(METADATA)
	@echo "TestTime:     15m" >> $(METADATA)
	@echo "Requires:     kvm" >> $(METADATA)
	@echo "Requires:     make" >> $(METADATA)
	@echo "Requires:     beaker-system-scan" >> $(METADATA)


