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

SELENIUM_SERVER_VERSION=1.0.3
SELENIUM_PYTHON_VERSION=2.2.0

.PHONY: all install download clean

# executables to be built should be added here, they will be generated on the system under test.
BUILT_FILES= 

DOWNLOADED_FILES=selenium-remote-control-$(SELENIUM_SERVER_VERSION).zip

# data files, .c files, scripts anything needed to either compile the test and/or run it.
FILES=$(METADATA) runtest.sh Makefile PURPOSE

run: $(FILES) build \
     /usr/lib/python2.4/site-packages/selenium-$(SELENIUM_PYTHON_VERSION)-py2.4.egg \
     /usr/local/share/selenium/selenium-server-$(SELENIUM_SERVER_VERSION)
	./runtest.sh

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh

download: $(DOWNLOADED_FILES)

selenium-remote-control-$(SELENIUM_SERVER_VERSION).zip:
	wget -nv http://selenium.googlecode.com/files/$@

clean:
	rm -f *~ *.rpm $(BUILT_FILES) $(DOWNLOADED_FILES)

/usr/local/share/selenium/selenium-server-$(SELENIUM_SERVER_VERSION): selenium-remote-control-$(SELENIUM_SERVER_VERSION).zip
	unzip -o -d /usr/local/share/selenium $<

/usr/lib/python2.4/site-packages/selenium-$(SELENIUM_PYTHON_VERSION)-py2.4.egg:
	easy_install 'selenium==$(SELENIUM_PYTHON_VERSION)'

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
	@echo "Environment:  BEAKER_CLIENT_COMMAND=bkr" >> $(METADATA)
	@echo "Environment:  NOSEARGS=bkr" >> $(METADATA)

	rhts-lint $(METADATA)
