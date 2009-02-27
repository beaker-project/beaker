%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %define pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

Name:           medusa
Version:        0.2
Release:        75%{?dist}
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
Requires: telnet

%description server
To Be Filled in - Server Side..

%description lab-controller
This is the interface to link Medusa and Cobbler together. Mostly provides
snippets and kickstarts.

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
%{__mkdir_p} %{buildroot}/var/www/cobbler/aux
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
%{__mkdir_p} %{buildroot}/var/lib/cobbler/triggers/install/pre
%{__mkdir_p} %{buildroot}/var/lib/cobbler/snippets
%{__mkdir_p} %{buildroot}/var/lib/cobbler/kickstarts

%{__install} -m 740 lab-controller/cron.daily/expire_distros %{buildroot}%{_sysconfdir}/cron.daily/
%{__install} lab-controller/triggers/sync/post/osversion.trigger %{buildroot}/var/lib/cobbler/triggers/sync/post/
%{__install} lab-controller/triggers/install/pre/clear_console_log.trigger %{buildroot}/var/lib/cobbler/triggers/install/pre/
%{__install} lab-controller/snippets/rhts_partitions %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/rhts_packages %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/rhts_pre %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/snippets/rhts_post %{buildroot}/var/lib/cobbler/snippets
%{__install} lab-controller/kickstarts/rhel3.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} lab-controller/kickstarts/rhel4.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} lab-controller/kickstarts/rhel5.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} lab-controller/kickstarts/fedora.ks %{buildroot}/var/lib/cobbler/kickstarts
%{__install} lab-controller/aux/rhts-checkin  %{buildroot}/var/www/cobbler/aux/
%{__install} -m 640 lab-controller/lib/cpioarchive.py %{buildroot}%{python_sitelib}/cpioarchive.py


%clean
%{__rm} -rf %{buildroot}

%files server
%defattr(-,root,root,-)
%doc README COPYING
%{python_sitelib}/%{name}/
%{_bindir}/start-%{name}
%{_bindir}/%{name}-*
%config(noreplace) %{_sysconfdir}/httpd/conf.d/medusa.conf
%attr(-,apache,root) %{_datadir}/%{name}
%attr(-,apache,root) %config(noreplace) %{_sysconfdir}/medusa/*
%attr(-,apache,root) %{_localstatedir}/log/medusa
%{python_sitelib}/%{name}-%{version}-py%{pyver}.egg-info/

%files lab-controller
%defattr(-,root,root,-)
%doc lab-controller/README
%{_sysconfdir}/cron.daily/expire_distros
%{python_sitelib}/cpioarchive.py*
/var/lib/cobbler/triggers/sync/post/osversion.trigger
/var/lib/cobbler/triggers/install/pre/clear_console_log.trigger
/var/lib/cobbler/snippets/*
/var/lib/cobbler/kickstarts/*
/var/www/cobbler/aux/rhts-checkin

%changelog
* Fri Feb 27 2009 Bill Peck <bpeck@redhat.com> - 0.2-74
- Require admin permissions on lab controller methods
- update default kickstarts to be closer to default installs
- update default kickstarts to be interactive if issued through pxe menu.
* Mon Feb 23 2009 Bill Peck <bpeck@redhat.com> - 0.2-73
- Added clear console log trigger
* Sun Feb 22 2009 Bill Peck <bpeck@redhat.com> - 0.2-72
- Added <cpu_count/> and <memory/> to XMl querying to speed up
  legacy access.  Two many self joins on key_table causes performance
  problems with mysql.
* Thu Feb 19 2009 Bill Peck <bpeck@redhat.com> - 0.2-71
- minor update for legacy push
* Wed Feb 18 2009 Bill Peck <bpeck@redhat.com> - 0.2-70
- pass kickstart file through if given one
* Wed Feb 18 2009 Bill Peck <bpeck@redhat.com> - 0.2-67
- fix traceback in system_return activity
* Wed Feb 18 2009 Bill Peck <bpeck@redhat.com> - 0.2-66
- Check for error in distro pick
* Wed Feb 18 2009 Bill Peck <bpeck@redhat.com> - 0.2-65
- Fix virt filter to work with False
* Wed Feb 18 2009 Bill Peck <bpeck@redhat.com> - 0.2-64
- Allow logging to be turned off for system_return
- filter distros by virt.
* Mon Feb 16 2009 Bill Peck <bpeck@redhat.com> - 0.2-63
- broke key_values into separate int and string tables.
- hopefully fixed available/free queries 

* Fri Feb 13 2009 Bill Peck <bpeck@redhat.com> - 0.2-62
- try number 2 on favicon.ico

* Fri Feb 13 2009 Bill Peck <bpeck@redhat.com> - 0.2-61
- added favicon.ico and fixed group lookup.

* Thu Feb 12 2009 Bill Peck <bpeck@redhat.com> - 0.2-60
- added robots.txt 

* Thu Feb 12 2009 Bill Peck <bpeck@redhat.com> - 0.2-59
- fix for importing tree info

* Wed Feb 11 2009 Bill Peck <bpeck@redhat.com> - 0.2-58
- fix for system history

* Wed Feb 11 2009 Bill Peck <bpeck@redhat.com> - 0.2-57
- added mac_address tracking for virt machines
- also track tree_path with distros

* Wed Feb 11 2009 Bill Peck <bpeck@redhat.com> - 0.2-56
- fix permissions on expire_distros

* Tue Feb 10 2009 Bill Peck <bpeck@redhat.com> - 0.2-55
- fix system query

* Tue Feb 10 2009 Bill Peck <bpeck@redhat.com> - 0.2-54
- fix logic in system.can_share()
- fix user sorting on main page
- allow searchbar to work for mine/available/free pages

* Tue Feb 10 2009 Bill Peck <bpeck@redhat.com> - 0.2-53
- rescan now pulls all distros, will look into caching later.

* Tue Feb 10 2009 Bill Peck <bpeck@redhat.com> - 0.2-52
- fixed delete logic, still haven't enabled delete by default
- added rescan method for lab controllers
- attempt to fix sorting by username

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-51
- fix scanning for deleted distros

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-50
- catch bad hostnames before trying to provision

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-49
- added rhts watchdog notification to rhts_pre snippet.

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-48
- Fix mispelling on BOOTARGS regex

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-47
- Paper bag fix

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-44
- Parse InstallPackage commands

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-43
- system activity for system_return was not being attached to system logs

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-42
- Disable expire code in labcontroller

* Thu Feb 05 2009 Bill Peck <bpeck@redhat.com> - 0.2-41
- Disable expire distros script for now.

* Wed Feb 04 2009 Bill Peck <bpeck@redhat.com> - 0.2-40
- Match existing rhts legacy repo name

* Wed Feb 04 2009 Bill Peck <bpeck@redhat.com> - 0.2-39
- Logging of returned systems
- return arch for distro pick
- pull runtests.sh for legacy rhts

* Wed Feb 04 2009 Bill Peck <bpeck@redhat.com> - 0.2-38
- Added system_return method

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-37
- Fixed bogus repo in rhts_post snippet

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-36
- Fixed netboot return code to match what legacy rhts expects

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-35
- Fixed system_pick and system_validate to return a host even when its busy.

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-34
- Added system filter method
- fixed user object in method system_pick

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-33
- Added system type filter method

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-32
- Added system_validate method 

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-31
- Updates for RHTS integration, lab controller selection.

* Tue Feb 03 2009 Bill Peck <bpeck@redhat.com> - 0.2-30
- Fixes for importing rawhide

* Wed Jan 07 2009 Bill Peck <bpeck@redhat.com> - 0.2-1
- Added lab-controller sub package

* Mon Dec 08 2008 Bill Peck <bpeck@redhat.com> - 0.1-1
- Initial Spec file Created.
