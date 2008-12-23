%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           medusa
Version:        0.1
Release:        1%{?dist}
Summary:        Inventory System
Group:          Applications/Internet
License:        GPLv2+
URL:            https://fedorahosted.org/beaker
Source0:        medusa-%{version}.tar.bz2

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch

BuildRequires: python-setuptools 
BuildRequires: python-setuptools-devel
BuildRequires: python-devel

BuildRequires: TurboGears

%description
To Be Filled in

%package server
Summary: Server component of Medusa
Group: Applications/Internet
Requires: TurboGears
Requires: python-TurboMail
Requires: intltool
Requires: python-fedora
Requires: python-decorator
Requires: python-xmltramp
Requires: mod_wsgi
Requires: python-tgexpandingformwidget


%description server
To Be Filled in - Server Side..

%prep
%setup -q
rm -rf medusa/tests medusa/tools/test-medusa.py

%build
%{__python} setup.py build --install-data=%{_datadir}

%install
%{__rm} -rf %{buildroot}
%{__python} setup.py install -O1 --skip-build \
    --install-data=%{_datadir} --root %{buildroot}

%{__mkdir_p} %{buildroot}/var/lib/medusa
%{__mkdir_p} %{buildroot}%{_sysconfdir}/httpd/conf.d
%{__mkdir_p} %{buildroot}%{_sysconfdir}/medusa
%{__mkdir_p} %{buildroot}%{_datadir}/%{name}
%{__mkdir_p} -m 0755 %{buildroot}/%{_localstatedir}/log/medusa

%{__install} -m 640 apache/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%{__install} -m 640 %{name}.cfg %{buildroot}%{_sysconfdir}/%{name}/
%{__install} apache/%{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi


%clean
%{__rm} -rf %{buildroot}


%files server
%defattr(-,root,root,-)
%doc README COPYING
%{python_sitelib}/%{name}/
%{_bindir}/start-%{name}
%{_bindir}/%{name}-*
%{_sysconfdir}/httpd/conf.d/medusa.conf
%attr(-,apache,root) %{_datadir}/%{name}
%attr(-,apache,root) %config(noreplace) %{_sysconfdir}/medusa/*
%attr(-,apache,root) %{_localstatedir}/log/medusa
%{python_sitelib}/%{name}-%{version}-py%{pyver}.egg-info/


%changelog
* Mon Dec 08 2008 Bill Peck <bpeck@redhat.com> - 0.1-1
- Initial Spec file Created.
