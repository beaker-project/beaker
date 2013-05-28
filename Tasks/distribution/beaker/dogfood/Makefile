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

SELENIUM_SERVER_VERSION=2.33.0

.PHONY: all install download clean

# executables to be built should be added here, they will be generated on the system under test.
BUILT_FILES= 

DOWNLOADED_FILES=selenium-server-standalone-$(SELENIUM_SERVER_VERSION).jar

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh update-config.sh Makefile PURPOSE $(DOWNLOADED_FILES)

run: $(FILES) build \
     /usr/local/share/selenium/selenium-server-standalone-$(SELENIUM_SERVER_VERSION).jar
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh

download: $(DOWNLOADED_FILES)

selenium-server-standalone-$(SELENIUM_SERVER_VERSION).jar:
	wget http://selenium.googlecode.com/files/$@

clean:
	rm -f *~ *.rpm $(BUILT_FILES) $(DOWNLOADED_FILES)

/usr/local/share/selenium/selenium-server-standalone-$(SELENIUM_SERVER_VERSION).jar: selenium-server-standalone-$(SELENIUM_SERVER_VERSION).jar
	mkdir -p $(@D)
	cp -p $< $@

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
	@echo "TestTime:     4h" >> $(METADATA)
	@echo "RunFor:       $(PACKAGE_NAME)-server" >> $(METADATA)  
	@echo "Requires:     $(PACKAGE_NAME)-integration-tests" >> $(METADATA)
	@echo "Requires:     python-nose" >> $(METADATA)  
	@echo "Requires:     kobo" >> $(METADATA)
	@echo "Requires:     java-1.6.0-openjdk" >> $(METADATA)  
	@echo "Requires:     Xvfb" >> $(METADATA)  
	@echo "Requires:     firefox" >> $(METADATA)  
	@echo "Requires:     @base-x" >> $(METADATA)  
	@echo "Requires:     @graphical-internet" >> $(METADATA)  
	@echo "Environment:  BEAKER_SERVER_BASE_URL=http://localhost/bkr/" >> $(METADATA)
#	@echo "Environment:  BEAKER_SKIP_INIT_DB=1" >> $(METADATA)
	@echo "Environment:  BEAKER_CONFIG_FILE=/etc/beaker/server.cfg" >> $(METADATA)
	@echo "Environment:  BEAKER_LABCONTROLLER_CONFIG_FILE=/etc/beaker/labcontroller.conf" >> $(METADATA)
	@echo "Environment:  BEAKER_CLIENT_COMMAND=bkr" >> $(METADATA)
	@echo "Environment:  NOSEARGS=bkr" >> $(METADATA)

	rhts-lint $(METADATA)
