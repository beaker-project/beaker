Name:		beah
Version:	0.1a1
Release:	1%{?dist}
Summary:	Beaker Test Harness

Group:		QA
License:	GPL
URL:		http://fedorahosted.org/beaker/wiki
Source0:	
Source1:	
BuildRoot:	%(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildRequires:	
Requires:	beah-python beah-python-twisted-core beah-python-twisted-web beah-python-simplejson
Packager:	Marian Csontos <mcsontos@rewdhat.com>

%description
Beah - Beaker Test Harness.

Ultimate Test Harness, with goal to serve any tests and any test scheduler
tools. Harness consist of a server and two kinds of clients - backends and
tasks.

Backends issue commands to Server and process events from tasks.
Tasks are mostly events producers.

Powered by Twisted.

%prep
%setup -q


%build
## %* - macros defined in /usr/lib/rpm/macros
%configure
%{__make}
#make %{?_smp_mflags}


%install
#rm -rf $RPM_BUILD_ROOT
%{__rm} -rf %{buildroot}
#make install DESTDIR=$RPM_BUILD_ROOT
%makeinstall


%clean
#rm -rf $RPM_BUILD_ROOT
%{__rm} -rf %{buildroot}


%files
%defattr(-,root,root,-)
%doc



%changelog
* 2009-09-01 - mcsontos@redhat.com
- initial version
