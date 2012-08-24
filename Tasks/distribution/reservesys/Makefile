# Include global Makefile targets
include /usr/share/rhts/lib/rhts-make.include

# The toplevel namespace within which the test lives.
TOPLEVEL_NAMESPACE=/distribution

# The path of the test below the package:
RELATIVE_PATH=reservesys

export TESTVERSION=2.0

export TEST=$(TOPLEVEL_NAMESPACE)/$(RELATIVE_PATH)

METADATA=testinfo.desc

# built executables should be added here
BUILT_FILES=$(METADATA)

FILES=$(BUILT_FILES) \
	runtest.sh   \
	recipe_status \
	Makefile

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh ./recipe_status

clean:
	rm -rf ./mnt
	rm -f *~ $(BUILT_FILES)
	rm -f rhts-rh-tests-distribution-install*.noarch.rpm

run: build
	./runtest.sh

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:		Bill Peck <bpeck@redhat.com>" > $(METADATA)
	@echo "Name:		$(TEST)"		>> $(METADATA)
	@echo "Path:		$(TEST_DIR)"		>> $(METADATA)
	@echo "TestVersion:	$(TESTVERSION)"		>> $(METADATA)
	@echo "Description:	Reserves system for specific time frame" >> $(METADATA)
	@echo "TestTime:	24h"			>> $(METADATA)
	@echo "Priority:	Manual"			>> $(METADATA)
	@echo "Requires:	emacs"			>> $(METADATA)
	@echo "Requires:	vim-enhanced"		>> $(METADATA)
	@echo "Requires:	unifdef"		>> $(METADATA)
	@echo "Requires:	sendmail"		>> $(METADATA)
	@echo "License:		GPLv2"	                >> $(METADATA)
	@echo "RhtsOptions:	-Compatible -CompatService"	>> $(METADATA)
