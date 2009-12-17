%define name beah
%define version 0.1.a1.dev200911202116
%define unmangled_version 0.1.a1.dev200911202116
%define unmangled_version 0.1.a1.dev200911202116
%define release 1

Summary: Beah - Beaker Test Harness. Part of Beaker project - http://fedorahosted.org/beaker/wiki.
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPL
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Marian Csontos <mcsontos@redhat.com>
Packager: Marian Csontos <mcsontos@redhat.com>
Requires: /usr/bin/python2.6
Requires: /usr/lib/python2.6/site-packages/setuptools
Requires: /usr/lib/python2.6/site-packages/simplejson
Requires: /usr/lib/python2.6/site-packages/zope/interface
Requires: /usr/lib/python2.6/site-packages/twisted
Requires: /usr/lib/python2.6/site-packages/twisted/web
Url: http://fedorahosted.org/beaker/wiki

%description
Beah - Beaker Test Harness.

Ultimate Test Harness, with goal to serve any tests and any test scheduler
tools. Harness consist of a server and two kinds of clients - backends and
tasks.

Backends issue commands to Server and process events from tasks.
Tasks are mostly events producers.

Powered by Twisted.


%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
%{__python} setup.py build

%install
%{__python} setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
