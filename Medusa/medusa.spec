%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           medusa
Version:        0.2
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
Requires: intltool
Requires: python-decorator
Requires: python-xmltramp
Requires: python-ldap
Requires: mod_wsgi
Requires: python-tgexpandingformwidget
Requires: httpd

%package lab-controller
Summary: Lab Controller xmlrpc server
Group: Applications/Internet
Requires: python
Requires: mod_python
Requires: httpd
Requires: cobbler >= 1.4
Requires: yum-utils 
Requires: /sbin/fenced

%description server
To Be Filled in - Server Side..

%description lab-controller
This is the interface to link Medusa and Cobbler together.

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
touch %{buildroot}/%{_localstatedir}/log/medusa/server.log

%{__install} -m 640 apache/%{name}.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/%{name}.conf
%{__install} -m 640 %{name}.cfg %{buildroot}%{_sysconfdir}/%{name}/
%{__install} apache/%{name}.wsgi %{buildroot}%{_datadir}/%{name}/%{name}.wsgi
%{__install} apache/xmlrpc_auth.wsgi %{buildroot}%{_datadir}/%{name}/xmlrpc_auth.wsgi

#lab-controller files
%{__mkdir_p} %{buildroot}/%{_sysconfdir}/cron.daily
%{__mkdir_p} %{buildroot}/var/lib/cobbler/triggers/sync/post
%{__mkdir_p} %{buildroot}/var/lib/cobbler/snippets
%{__mkdir_p} %{buildroot}/var/lib/cobbler/kickstarts
%{__mkdir_p} %{buildroot}/var/www/labcontroller

%{__install} -m 640 lab-controller/conf.d/labcontroller.conf %{buildroot}%{_sysconfdir}/httpd/conf.d/
%{__install} -m 640 lab-controller/cron.daily/expire_distros %{buildroot}%{_sysconfdir}/cron.daily/
%{__install} lab-controller/www/labcontroller.py %{buildroot}/var/www/labcontroller/
%{__install} lab-controller/www/xmlrpc.py %{buildroot}/var/www/labcontroller/
%{__install} lab-controller/triggers/osversion.trigger %{buildroot}/var/lib/cobbler/triggers/sync/post/
%{__install} lab-controller/snippets/rhts_recipe %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/main_packages_select %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/pre_packages_select %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/rhts_pre_partition_select %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/rhts_post_install_kernel_options %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/kickstarts/rhel4.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} lab-controller/kickstarts/rhel5.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} -m 640 lab-controller/lib/cpioarchive.py %{buildroot}%{python_sitelib}/cpioarchive.py


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

%files lab-controller
%defattr(-,root,root,-)
%doc lab-controller/README
%attr(-,apache,root) /var/www/labcontroller/*
%{_sysconfdir}/httpd/conf.d/labcontroller.conf
%{_sysconfdir}/cron.daily/expire_distros
%{python_sitelib}/cpioarchive.py*
/var/lib/cobbler/triggers/sync/post/osversion.trigger
/var/lib/cobbler/snippets/*
/var/lib/cobbler/kickstarts/*

%changelog
* Wed Jan 07 2009 Bill Peck <bpeck@redhat.com> - 0.2-1
- Added lab-controller sub package

* Mon Dec 08 2008 Bill Peck <bpeck@redhat.com> - 0.1-1
- Initial Spec file Created.
