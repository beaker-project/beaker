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
# Author: Petr Muller <pmuller@redhat.com>

VERSION=0.6
RELEASE=1
SCRIPTS=rhtslib.sh\
		journal.sh\
		logging.sh\
		testing.sh\
		rpms.sh\
		infrastructure.sh\
		performance.sh\
		analyze.sh\
		virtualX.sh
FILES=rhtslib.spec $(SCRIPTS)
PYTFILES=python/rlMemAvg.py\
	python/rlMemPeak.py\
	python/journalling.py\
	python/journal-compare.py
PERLFILES=perl/deja-summarize

MANDIR=docs/man
WIKIDIR=docs/wiki
WIKIPREFIX="Docs(2f)RhtsLibrary(2f)Manual(2f)"
WIKILOCATION="wikiadmin@docs.example.com:/var/www/moin/wiki/data/pages"

.PHONY: tarball install release check clean unit-test relstall

tarball: $(FILES) docsman gendict
	rm -rf rhtslib-$(VERSION)/
	mkdir rhtslib-$(VERSION)/
	cp -pr $(FILES) Makefile dictionary.vim test/ rhtslib-$(VERSION)/
	rm -rf rhtslib-$(VERSION)/test/remotedir rhtslib-$(VERSION)/test/rhtslib-test-mount-point
	mkdir rhtslib-$(VERSION)/python/
	cp -pr $(PYTFILES) rhtslib-$(VERSION)/python/
	mkdir rhtslib-$(VERSION)/perl/
	cp -pr $(PERLFILES) rhtslib-$(VERSION)/perl/
	cp -p perl/docsjoin rhtslib-$(VERSION)/perl/
	mkdir -p rhtslib-$(VERSION)/$(MANDIR)/
	cp -pr $(MANDIR)/man1 rhtslib-$(VERSION)/$(MANDIR)/
	tar -czf rhtslib-$(VERSION).tar.gz rhtslib-$(VERSION)/
	rm -rf rhtslib-$(VERSION)/

rhtslib-$(VERSION).tar.gz: tarball

install: $(FILES)
	mkdir -p $(DESTDIR)/usr/share/rhts-library
	mkdir -p $(DESTDIR)/usr/share/rhts-library/python	
	mkdir -p $(DESTDIR)/usr/share/rhts-library/perl
	mkdir -p $(DESTDIR)/usr/share/rhts-library/test
	mkdir -p $(DESTDIR)/usr/share/man/man1

	cp $(FILES) dictionary.vim $(DESTDIR)/usr/share/rhts-library
	cp $(PYTFILES) $(DESTDIR)/usr/share/rhts-library/python
	cp $(PERLFILES) $(DESTDIR)/usr/share/rhts-library/perl
	cp test/* $(DESTDIR)/usr/share/rhts-library/test
	cp $(MANDIR)/man1/* $(DESTDIR)/usr/share/man/man1
	rm $(DESTDIR)/usr/share/rhts-library/rhtslib.spec

clean:
	rm -f *.tar.gz
	rm -f test/runtests-worker.sh
	rm -rf docs/{man,wiki,html,pod}
	rm -f ./pod2htm*
	rm -f dictionary.vim
	
check:
	RHTSLIB=. sh rhtslib.sh	

unit-test:
	cd test/; ./runtests.sh

docsjoin:
	rm -rf docs/pod
	mkdir -p docs/pod
	./perl/docsjoin $(SCRIPTS) >docs/pod/rhtslib.pod

docsman: $(SCRIPTS) docsjoin
	rm -rf docs/man
	mkdir -p docs/man/man1
	for i in $(SCRIPTS); do \
		name=`echo $$i | sed 's/\.sh//'`; \
	    pod2man $$i > docs/man/man1/rhtslib-$$name.1; \
	done
	pod2man docs/pod/rhtslib.pod > docs/man/man1/rhtslib.1
	gzip docs/man/man1/*.1

docshtml: $(SCRIPTS) docsjoin
	rm -rf docs/html
	mkdir -p docs/html
	for i in $(SCRIPTS); do \
		name=`echo $$i | sed 's/\.sh//'`; \
	    pod2html $$i > docs/html/rhtslib-$$name.html; \
	done
	pod2html docs/pod/rhtslib.pod > docs/html/rhtslib.html

docswiki: $(SCRIPTS) docsjoin
	rm -rf $(WIKIDIR)
	if ! type pod2wiki &>/dev/null; then \
	    echo "You need pod2wiki utility - see package 'perl-Pod-Simple-Wiki' or http://search.cpan.org/dist/Pod-Simple-Wiki/"; \
	    false; \
	fi
	if pod2wiki 2>&1 | grep -q "Can't locate Pod/Simple/Wiki"; then \
	    echo "You need Pod::Simple::Wiki module for converting to wiki"; \
	    echo "Try: yum install perl-CPAN && perl -MCPAN -e 'install \"Pod::Simple::Wiki\"'"; \
	    false; \
	fi
	cp docs/pod/rhtslib.pod RhtslibManual
	for i in $(SCRIPTS) RhtslibManual; do \
	    MODULE=`echo $$i | sed 's/^\(.*\).sh$$/\u\1/' | sed 's/-\([^-]\)/\u\1/g'`; \
	    MODULEDIR=$(WIKIDIR)/$(WIKIPREFIX)$$MODULE; \
	    mkdir -p $$MODULEDIR/revisions; \
		 echo 00000001 > $$MODULEDIR/current; \
		 echo '<<TableOfContents(4)>>' > $$MODULEDIR/revisions/00000001; \
	    pod2wiki --style moinmoin $$i >> $$MODULEDIR/revisions/00000001; \
	done
	rm RhtslibManual

gendict:
	RHTSLIB=. bash -c ". rhtslib.sh ; declare -f |grep '^rl.* ()' |cut -d ' ' -f 1 > dictionary.vim"

wiki: $(SCRIPTS) docswiki
	scp -r $(WIKIDIR)/* $(WIKILOCATION)

docs: docshtml docsman wiki

srpm: rhtslib-$(VERSION).tar.gz
	rpmbuild -ts $<

release: clean check tarball
	mkdir -p ~/rpmbuild/SOURCES
	cp rhtslib-$(VERSION).tar.gz ~/rpmbuild/SOURCES/
	rpmbuild -ba rhtslib.spec

relstall: release
	sudo rpm -Uhv --force ~/rpmbuild/RPMS/noarch/rhtslib-$(VERSION)-$(RELEASE)*rpm

publish: release
	cp ~/rpmbuild/RPMS/noarch/rhtslib-$(VERSION)-$(RELEASE)*rpm /var/www/html/
	rm -f /var/www/html/rhtslib.rpm /var/www/html/rhtslib.noarch.rpm
	ln -s rhtslib-$(VERSION)-$(RELEASE).noarch.rpm /var/www/html/rhtslib.rpm
	ln -s rhtslib-$(VERSION)-$(RELEASE).noarch.rpm /var/www/html/rhtslib.noarch.rpm
	file /var/www/html/rhtslib.rpm
	file /var/www/html/rhtslib.noarch.rpm
