# Include global Makefile targets
include /usr/share/rhts/lib/rhts-make.include

# The toplevel namespace within which the test lives.
TOPLEVEL_NAMESPACE=/beah-tests

# The path of the test below the package:
RELATIVE_PATH=beah_update

export TESTVERSION=1.1

export TEST=$(TOPLEVEL_NAMESPACE)/$(RELATIVE_PATH)

METADATA=testinfo.desc

# built executables should be added here
BUILT_FILES=$(METADATA)

FILES=$(BUILT_FILES) runtest.sh Makefile PURPOSE

build: $(BUILT_FILES)
	chmod a+x ./runtest.sh

clean:
	rm -rf *.rpm *~ $(BUILT_FILES)

run: build
	./runtest.sh

# Generate the testinfo.desc here:
$(METADATA): Makefile
	@touch $(METADATA)
	@echo "Owner:		Marian Csontos <mcsontos@redhat.com>" > $(METADATA)
	@echo "Name:		$(TEST)"		>> $(METADATA)
	@echo "Path:		$(TEST_DIR)"		>> $(METADATA)
	@echo "TestVersion:	$(TESTVERSION)"		>> $(METADATA)
	@echo "Description:	Update harness from git." >> $(METADATA)
	@echo "TestTime:	5m"			>> $(METADATA)
	@echo "Priority:	Manual"			>> $(METADATA)
	@echo "Requires:	git"		>> $(METADATA)
	@echo "License:		GNU GPL 2"	>> $(METADATA)

