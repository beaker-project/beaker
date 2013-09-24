%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %global pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

# The server, lab controller, and integration test subpackages can be conditionally built.
# Enabled on RHEL 6 and F18+
# Use rpmbuild --with/--without to override.
%if 0%{?rhel} == 6 || 0%{?fedora} >= 18
%bcond_without server
%bcond_without labcontroller
%bcond_without inttests
%else
%bcond_with server
%bcond_with labcontroller
%bcond_with inttests
%endif
%global _lc_services beaker-proxy beaker-provision beaker-watchdog beaker-transfer
# systemd?
%if 0%{?fedora} >= 18 || 0%{?rhel} >= 7
%global with_systemd 1
%else
%global with_systemd 0
%endif

%global upstream_version 0.14.1

# Note: While some parts of this file use "%{name}, "beaker" is still
# hardcoded in a lot of places, both here and in the source code
Name:           beaker
Version:        0.14.1
Release:        1%{?dist}
Summary:        Filesystem layout for Beaker
Group:          Applications/Internet
License:        GPLv2+
URL:            http://beaker-project.org/
Source0:        http://beaker-project.org/releases/%{name}-%{upstream_version}.tar.gz
BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  make
BuildRequires:  python-setuptools
BuildRequires:  python-setuptools-devel
BuildRequires:  python2-devel
BuildRequires:  python-docutils >= 0.6
%if 0%{?rhel} == 5 || 0%{?rhel} == 6
BuildRequires:  python-sphinx10
%else
BuildRequires:  python-sphinx >= 1.0
%endif
BuildRequires:  python-sphinxcontrib-httpdomain
BuildRequires:  bash-completion

%if %{with server}
BuildRequires:  python-kid
# These server dependencies are needed in the build, because
# sphinx imports bkr.server modules to generate API docs
BuildRequires:  TurboGears >= 1.1.3
%if 0%{?rhel} == 6
BuildRequires:  python-turbojson13
%else
BuildRequires:  python-turbojson
%endif
BuildRequires:  python-sqlalchemy >= 0.6
BuildRequires:  python-xmltramp
BuildRequires:  python-lxml
BuildRequires:  python-ldap
BuildRequires:  python-TurboMail >= 3.0
BuildRequires:  cracklib-python
BuildRequires:  rpm-python
BuildRequires:  rhts-python
BuildRequires:  python-netaddr
BuildRequires:  ovirt-engine-sdk
BuildRequires:  python-itsdangerous
BuildRequires:  python-decorator
BuildRequires:  python-flask
BuildRequires:  python-markdown
BuildRequires:  python-webassets
%if %{with_systemd}
BuildRequires:  systemd
%endif

%endif

# As above, these client dependencies are needed in build because of sphinx
BuildRequires:  kobo-client >= 0.3
BuildRequires:  python-krbV
BuildRequires:  python-lxml
BuildRequires:  libxslt-python


%package client
Summary:        Client component for talking to Beaker server
Group:          Applications/Internet
Requires:       python
Requires:       kobo-client >= 0.3
Requires:	python-setuptools
Requires:	%{name} = %{version}-%{release}
Requires:       python-krbV
Requires:       python-lxml
%if 0%{?rhel} >= 6 || 0%{?fedora}
# some client commands use requests, they are unsupported on RHEL5
Requires:       python-requests
%endif
Requires:       libxslt-python
%if !(0%{?rhel} >= 6) || !(0%{?fedora} >= 14)
Requires:       python-simplejson
%endif
Requires:       libxml2-python
# beaker-wizard was moved from rhts-devel to here in 4.52
Conflicts:      rhts-devel < 4.52

%if %{with server}
%package server
Summary:       Server component of Beaker
Group:          Applications/Internet
Requires:       TurboGears >= 1.1.3
%if 0%{?rhel} == 6
Requires:       python-turbojson13
%else
Requires:       python-turbojson
%endif
Requires:       python-sqlalchemy >= 0.6
Requires:       intltool
Requires:       python-decorator
Requires:       python-xmltramp
Requires:       python-lxml
Requires:       python-ldap
Requires:       python-rdflib >= 3.2.0
Requires:       python-daemon
Requires:       python-lockfile >= 0.9
Requires:       mod_wsgi
Requires:       python-tgexpandingformwidget
Requires:       httpd
Requires:       python-krbV
Requires:	%{name} = %{version}-%{release}
Requires:       python-TurboMail >= 3.0
Requires:	createrepo
Requires:	yum-utils
Requires:       rhts-python
Requires:       cracklib-python
Requires:       python-jinja2
Requires:       python-netaddr
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       ovirt-engine-sdk
Requires:  	kobo-client >= 0.3
Requires:       python-itsdangerous
Requires:       python-decorator
Requires:       python-flask
Requires:       python-markdown
Requires:       python-webassets
%if %{with_systemd}
Requires:       systemd-units
Requires(post): systemd
Requires(pre):  systemd
Requires(postun):  systemd
%endif
%endif


%if %{with inttests}
%package integration-tests
Summary:        Integration tests for Beaker
Group:          Applications/Internet
Requires:       %{name} = %{version}-%{release}
Requires:       %{name}-server = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       python-nose >= 0.10
Requires:       selenium-python >= 2.12
Requires:       kobo
Requires:       java-openjdk >= 1:1.6.0
Requires:       Xvfb
Requires:       firefox
Requires:       lsof
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       openldap-servers
Requires:       python-unittest2
Requires:       python-gunicorn
%endif


%if %{with labcontroller}
%package lab-controller
Summary:        Lab Controller xmlrpc server
Group:          Applications/Internet
Provides:       beaker-redhat-support <= 0.19
Obsoletes:      beaker-redhat-support <= 0.19
Requires:       python
Requires:       httpd
Requires:       cobbler >= 1.4
Requires:       yum-utils
Requires:       fence-agents
Requires:       ipmitool
Requires:       wsmancli
Requires:       telnet
Requires:       sudo
Requires:       python-cpio
Requires:	%{name} = %{version}-%{release}
Requires:       kobo >= 0.3.2
Requires:	kobo-client
Requires:	python-setuptools
Requires:	python-xmltramp
Requires:       python-krbV
Requires:       python-gevent >= 1.0
Requires:       python-daemon
Requires:       python-werkzeug
%if %{with_systemd}
Requires:       systemd-units
Requires(post): systemd
Requires(pre):  systemd
Requires(postun):  systemd
%endif

%package lab-controller-addDistro
Summary:        addDistro scripts for Lab Controller
Group:          Applications/Internet
Requires:       %{name} = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}
Provides:	beaker-redhat-support-addDistro
Obsoletes:	beaker-redhat-support-addDistro
%endif


%description
Filesystem layout for beaker


%description client
This is the command line interface used to interact with the Beaker Server.


%if %{with server}
%description server
To Be Filled in - Server Side..
%endif


%if %{with inttests}
%description integration-tests
This package contains integration tests for Beaker, which require a running 
database and Beaker server.
%endif


%if %{with labcontroller}
%description lab-controller
This is the interface to link Medusa and Cobbler together. Mostly provides
snippets and kickstarts.

%description lab-controller-addDistro
addDistro.sh can be called after distros have been imported into beaker.
Automatically launch jobs against newly imported distros.
%endif

%prep
%setup -q -n %{name}-%{upstream_version}

%build
[ "$RPM_BUILD_ROOT" != "/" ] && [ -d $RPM_BUILD_ROOT ] && rm -rf $RPM_BUILD_ROOT;
DESTDIR=$RPM_BUILD_ROOT make \
    %{?with_server:WITH_SERVER=1} \
    %{?with_labcontroller:WITH_LABCONTROLLER=1} \
    %{?with_inttests:WITH_INTTESTS=1}

%install
DESTDIR=$RPM_BUILD_ROOT make \
    %{?with_server:WITH_SERVER=1} \
    %{?with_labcontroller:WITH_LABCONTROLLER=1} \
    %{?with_inttests:WITH_INTTESTS=1} \
    install

%if %{with_systemd}
mkdir -p  $RPM_BUILD_ROOT%{_tmpfilesdir}
cp -p Server/tmpfiles.d/beaker-server.conf $RPM_BUILD_ROOT%{_tmpfilesdir}/beaker-server.conf
cp -p LabController/tmpfiles.d/beaker-lab-controller.conf $RPM_BUILD_ROOT%{_tmpfilesdir}/beaker-lab-controller.conf
%endif


%clean
%{__rm} -rf %{buildroot}

%if %{with server}

%post server
%if %{with_systemd}
%systemd_post beakerd.service
%else
/sbin/chkconfig --add beakerd
%endif
# Migrate ConcurrentLogHandler -> syslog
rm -f %{_localstatedir}/log/%{name}/*.lock >/dev/null 2>&1 || :
chown root:root %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
chmod go-w %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
# Restart rsyslog so that it notices the config which we ship
/sbin/service rsyslog condrestart >/dev/null 2>&1 || :
%endif

%if %{with labcontroller}

%post lab-controller
%if %{with_systemd}
%systemd_post %{_lc_services}
%else
for service in %{_lc_services}; do
    /sbin/chkconfig --add $service
done
%endif
# Migrate ConcurrentLogHandler -> syslog
rm -f %{_localstatedir}/log/%{name}/*.lock >/dev/null 2>&1 || :
chown root:root %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
chmod go-w %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
# Restart rsyslog so that it notices the config which we ship
/sbin/service rsyslog condrestart >/dev/null 2>&1 || :
%endif

%if %{with server}
%postun server
%if %{with_systemd}
%systemd_postun_with_restart beakerd.service
%else
if [ "$1" -ge "1" ]; then
    /sbin/service beakerd condrestart >/dev/null 2>&1 || :
fi
%endif
%endif

%if %{with labcontroller}
%postun lab-controller
%if %{with_systemd}
%systemd_postun_with_restart %{_lc_services}
%else
if [ "$1" -ge "1" ]; then
   for service in %{_lc_services}; do
       /sbin/service $service condrestart >/dev/null 2>&1 || :
   done
fi
%endif
%endif

%if %{with server}
%preun server
%if %{with_systemd}
%systemd_preun beakerd.service
%else
if [ "$1" -eq "0" ]; then
        /sbin/service beakerd stop >/dev/null 2>&1 || :
        /sbin/chkconfig --del beakerd || :
fi
%endif
%endif

%if %{with labcontroller}
%preun lab-controller
%if %{with_systemd}
%systemd_preun %{_lc_services}
%else
if [ "$1" -eq "0" ]; then
      for service in %{_lc_services}; do
          /sbin/service $service stop >/dev/null 2>&1 || :
          /sbin/chkconfig --del $service || :
      done
fi
rm -rf %{_var}/lib/beaker/osversion_data
%endif
%endif

%files
%defattr(-,root,root,-)
%{python_sitelib}/bkr/__init__.py*
%{python_sitelib}/bkr/timeout_xmlrpclib.py*
%{python_sitelib}/bkr/common/
%{python_sitelib}/bkr/log.py*
%{python_sitelib}/bkr-*.egg-info/
%doc COPYING

%if %{with server}
%files server
%defattr(-,root,root,-)
%doc documentation/_build/text/whats-new/
%{python_sitelib}/bkr/server/
%{python_sitelib}/bkr.server-*-nspkg.pth
%{python_sitelib}/bkr.server-*.egg-info/
%{_bindir}/%{name}-init
%{_bindir}/nag-mail
%{_bindir}/log-delete
%{_bindir}/beaker-check
%{_bindir}/product-update
%{_bindir}/beaker-repo-update
%{_bindir}/beaker-sync-tasks
%{_bindir}/beaker-refresh-ldap

%if %{with_systemd}
%{_unitdir}/beakerd.service
%exclude %{_sysconfdir}/init.d
%else
%{_sysconfdir}/init.d/%{name}d
%exclude /usr/lib/systemd
%endif

%config(noreplace) %{_sysconfdir}/cron.d/%{name}
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-server.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker
%attr(0755,root,root)%{_bindir}/%{name}d
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}-server.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/%{name}-server.wsgi
%attr(-,apache,root) %{_datadir}/bkr/server
%attr(0660,apache,root) %config(noreplace) %{_sysconfdir}/%{name}/server.cfg
%dir %{_localstatedir}/log/%{name}
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/logs
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/rpms
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/repos
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}
%attr(-,apache,root) %dir %{_localstatedir}/lib/%{name}
%if %{with_systemd}
%attr(0644,apache,apache) %{_tmpfilesdir}/beaker-server.conf
%endif
%endif

%if %{with inttests}
%files integration-tests
%defattr(-,root,root,-)
%{python_sitelib}/bkr/inttest/
%{python_sitelib}/bkr.inttest-*-nspkg.pth
%{python_sitelib}/bkr.inttest-*.egg-info/
%endif

%files client
%defattr(-,root,root,-)
%doc Client/client.conf.example
%{python_sitelib}/bkr/client/
%{python_sitelib}/bkr.client-*-nspkg.pth
%{python_sitelib}/bkr.client-*.egg-info/
%{_bindir}/beaker-wizard
%{_bindir}/bkr
%{_mandir}/man1/*.1.gz
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%{_datadir}/bash-completion
%else
%{_sysconfdir}/bash_completion.d
%endif

%if %{with labcontroller}
%files lab-controller
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/beaker/labcontroller.conf
%{_sysconfdir}/beaker/power-scripts/
%{python_sitelib}/bkr/labcontroller/
%{python_sitelib}/bkr.labcontroller-*-nspkg.pth
%{python_sitelib}/bkr.labcontroller-*.egg-info/
%{_bindir}/%{name}-proxy
%{_bindir}/%{name}-watchdog
%{_bindir}/%{name}-transfer
%{_bindir}/%{name}-import
%{_bindir}/%{name}-provision
%{_bindir}/%{name}-pxemenu
%{_bindir}/%{name}-expire-distros
%{_bindir}/%{name}-clear-netboot
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}-lab-controller.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/lab-controller
%config(noreplace) %{_sysconfdir}/cron.hourly/beaker_expire_distros
%attr(-,apache,root) %dir %{_var}/www/beaker
%attr(-,apache,root) %dir %{_var}/www/beaker/logs
%dir %{_localstatedir}/log/%{name}

%if %{with_systemd}
%{_unitdir}/beaker-proxy.service
%{_unitdir}/beaker-provision.service
%{_unitdir}/beaker-watchdog.service
%{_unitdir}/beaker-transfer.service
%exclude %{_sysconfdir}/init.d
%else
%{_sysconfdir}/init.d/%{name}-proxy
%{_sysconfdir}/init.d/%{name}-watchdog
%{_sysconfdir}/init.d/%{name}-transfer
%{_sysconfdir}/init.d/%{name}-provision
%exclude /usr/lib/systemd
%endif

%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}-lab-controller
%attr(0440,root,root) %config(noreplace) %{_sysconfdir}/sudoers.d/%{name}_proxy_clear_netboot
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-lab-controller.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker
%if %{with_systemd}
%attr(0644,apache,apache) %{_tmpfilesdir}/beaker-lab-controller.conf
%endif

%files lab-controller-addDistro
%defattr(-,root,root,-)
%{_var}/lib/beaker/addDistro.sh
%{_var}/lib/beaker/addDistro.d/*
%endif

%changelog
