Name: rhtslib
Summary: RHTS test library
Version: 	0.6
Release: 	3
License: 	GPLv2
Group: 		QA
BuildRoot:  %{_tmppath}/%{name}-%{version}-root
Source0:	%{name}-%{version}.tar.gz
BuildArch:	noarch
URL:            https://fedorahosted.org/beaker/RhtsLibrary

%description
The rhtslib project means to provide a library of various helpers,
which could be used when writing RHTS tests.

%prep
%setup -q

%build

%install
%makeinstall DESTDIR=$RPM_BUILD_ROOT
rm perl/docsjoin
 
%clean
[ "$RPM_BUILD_ROOT" != "/" ] && [ -d $RPM_BUILD_ROOT ] && rm -rf $RPM_BUILD_ROOT;

%files
/usr/share/rhts-library/testing.sh
/usr/share/rhts-library/rpms.sh
/usr/share/rhts-library/logging.sh
/usr/share/rhts-library/journal.sh
/usr/share/rhts-library/infrastructure.sh
/usr/share/rhts-library/rhtslib.sh
/usr/share/rhts-library/analyze.sh
/usr/share/rhts-library/performance.sh
/usr/share/rhts-library/dictionary.vim
/usr/share/rhts-library/virtualX.sh
/usr/share/rhts-library/python/rlMemAvg.py
/usr/share/rhts-library/python/rlMemPeak.py
/usr/share/rhts-library/python/rlMemAvg.pyc
/usr/share/rhts-library/python/rlMemAvg.pyo
/usr/share/rhts-library/python/rlMemPeak.pyc
/usr/share/rhts-library/python/rlMemPeak.pyo
/usr/share/rhts-library/python/journalling.py
/usr/share/rhts-library/python/journalling.pyc
/usr/share/rhts-library/python/journalling.pyo
/usr/share/rhts-library/python/journal-compare.py
/usr/share/rhts-library/python/journal-compare.pyc
/usr/share/rhts-library/python/journal-compare.pyo
/usr/share/rhts-library/perl/deja-summarize
/usr/share/rhts-library/test/README
/usr/share/rhts-library/test/coverageTest.sh
/usr/share/rhts-library/test/infrastructureTest.sh
/usr/share/rhts-library/test/journalTest.sh
/usr/share/rhts-library/test/library.sh
/usr/share/rhts-library/test/loggingTest.sh
/usr/share/rhts-library/test/rhtslibTest.sh
/usr/share/rhts-library/test/rpmsTest.sh
/usr/share/rhts-library/test/runtests.sh
/usr/share/rhts-library/test/shunit2
/usr/share/rhts-library/test/testingTest.sh
/usr/share/man/man1/rhtslib-rpms.1.gz
/usr/share/man/man1/rhtslib.1.gz
/usr/share/man/man1/rhtslib-virtualX.1.gz
/usr/share/man/man1/rhtslib-infrastructure.1.gz
/usr/share/man/man1/rhtslib-analyze.1.gz
/usr/share/man/man1/rhtslib-rhtslib.1.gz
/usr/share/man/man1/rhtslib-performance.1.gz
/usr/share/man/man1/rhtslib-testing.1.gz
/usr/share/man/man1/rhtslib-journal.1.gz
/usr/share/man/man1/rhtslib-logging.1.gz

