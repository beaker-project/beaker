# Copyright (c) 2010 Red Hat, Inc. All rights reserved. This copyrighted material 
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
RELATIVE_PATH=dogfood
export TESTVERSION=1.1
export TEST=/$(TOPLEVEL_NAMESPACE)/$(PACKAGE_NAME)/$(RELATIVE_PATH)

.PHONY: all install download clean

# executables to be built should be added here, they will be generated on the system under test.
BUILT_FILES= 

DOWNLOADED_FILES=selenium-remote-control-1.0.3.zip

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh Makefile PURPOSE

run: $(FILES) build \
     /usr/lib/python2.4/site-packages/selenium-2.0a5-py2.4.egg \
     /usr/local/share/selenium/selenium-server-1.0.3
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh

download: $(DOWNLOADED_FILES)

selenium-remote-control-1.0.3.zip:
	wget -nv http://selenium.googlecode.com/files/$@

clean:
	rm -f *~ *.rpm $(BUILT_FILES) $(DOWNLOADED_FILES)

/usr/local/share/selenium/selenium-server-1.0.3: selenium-remote-control-1.0.3.zip
	unzip -o -d /usr/local/share/selenium $<

/usr/lib/python2.4/site-packages/selenium-2.0a5-py2.4.egg:
	easy_install 'selenium==2.0a5'

# Include Common Makefile
include /usr/share/rhts/lib/rhts-make.include

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:        Dan Callaghan <dcallagh@redhat.com>" > $(METADATA)
	@echo "Name:         $(TEST)" >> $(METADATA)
	@echo "Path:         $(TEST_DIR)"	>> $(METADATA)
	@echo "License:      GPL-2" >> $(METADATA)
	@echo "TestVersion:  $(TESTVERSION)"	>> $(METADATA)
	@echo "Description:  Runs Beaker's internal test suite" >> $(METADATA)
	@echo "TestTime:     30m" >> $(METADATA)
	@echo "RunFor:       $(PACKAGE_NAME)-server" >> $(METADATA)  
	@echo "Requires:     $(PACKAGE_NAME)-server" >> $(METADATA)  
	@echo "Requires:     python-nose" >> $(METADATA)  
	@echo "Requires:     kobo" >> $(METADATA)
	@echo "Requires:     java-1.6.0-openjdk" >> $(METADATA)  

	rhts-lint $(METADATA)
