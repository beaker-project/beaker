%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%endif

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

# This will not necessarily match the RPM Version if the real version number is 
# not representable in RPM. For example, a release candidate might be 0.15.0rc1 
# but that is not usable for the RPM Version because it sorts higher than 
# 0.15.0, so the RPM will have Version 0.15.0 and Release 0.rc1 in that case.
%global upstream_version 0.16.1

# Note: While some parts of this file use "%{name}, "beaker" is still
# hardcoded in a lot of places, both here and in the source code
Name:           beaker
Version:        0.16.1
Release:        1%{?dist}
Summary:        Filesystem layout for Beaker
Group:          Applications/Internet
License:        GPLv2+ and BSD
URL:            http://beaker-project.org/

Source0:        http://beaker-project.org/releases/%{name}-%{upstream_version}.tar.gz
# Third-party JS/CSS libraries which are built into Beaker's generated JS/CSS
# (these are submodules in Beaker's git tree, the commit hashes here should
# correspond to the submodule commits)
Source1:        https://github.com/twbs/bootstrap/archive/d9b502dfb876c40b0735008bac18049c7ee7b6d2/bootstrap-d9b502dfb876c40b0735008bac18049c7ee7b6d2.tar.gz
Source2:        https://github.com/FortAwesome/Font-Awesome/archive/b1a8ad47303509e70e56079396fad2afadfd96d5/font-awesome-b1a8ad47303509e70e56079396fad2afadfd96d5.tar.gz
Source3:        https://github.com/twitter/typeahead.js/archive/2bd1119ecdd5ed4bb6b78c83b904d70adc49e023/typeahead.js-2bd1119ecdd5ed4bb6b78c83b904d70adc49e023.tar.gz
Source4:        https://github.com/jashkenas/underscore/archive/edbf2952c2b71f81c6449aef384bdf233a0d63bc/underscore-edbf2952c2b71f81c6449aef384bdf233a0d63bc.tar.gz
Source5:        https://github.com/jashkenas/backbone/archive/699fe3271262043bb137bae97bd0003d6d193f27/backbone-699fe3271262043bb137bae97bd0003d6d193f27.tar.gz

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  make
BuildRequires:  python-setuptools
BuildRequires:  python-nose >= 0.10
BuildRequires:  python-unittest2
BuildRequires:  python-setuptools-devel
BuildRequires:  python2-devel
BuildRequires:  python-docutils >= 0.6
%if 0%{?rhel} == 5 || 0%{?rhel} == 6
BuildRequires:  python-sphinx10
%else
BuildRequires:  python-sphinx >= 1.0
%endif
BuildRequires:  python-sphinxcontrib-httpdomain
BuildRequires:  python-prettytable
# setup.py uses pkg-config to find the right installation paths
%if 0%{?fedora} || 0%{?rhel} >= 7
BuildRequires:  pkgconfig(bash-completion)
%endif
%if %{with_systemd}
BuildRequires:  pkgconfig(systemd)
%endif

%if %{with server}
BuildRequires:  python-kid
BuildRequires:  python-webassets
BuildRequires:  /usr/bin/lessc
BuildRequires:  /usr/bin/cssmin
BuildRequires:  /usr/bin/uglifyjs
# These runtime dependencies are needed at build time as well, because
# the unit tests and Sphinx autodoc import the server code as part of the
# build process.
BuildRequires:  createrepo
BuildRequires:  createrepo_c
BuildRequires:  python-requests
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
BuildRequires:  python-netaddr
BuildRequires:  ovirt-engine-sdk
BuildRequires:  python-itsdangerous
BuildRequires:  python-decorator
BuildRequires:  python-flask
BuildRequires:  python-markdown
BuildRequires:  python-passlib
%if %{with_systemd}
BuildRequires:  systemd
%endif

%endif

# As above, these client dependencies are needed in build because of sphinx
BuildRequires:  python-krbV
BuildRequires:  python-lxml
BuildRequires:  libxslt-python


%package client
Summary:        Client component for talking to Beaker server
Group:          Applications/Internet
Requires:       python
Requires:       python-setuptools
Requires:       %{name} = %{version}-%{release}
Requires:       python-krbV
Requires:       python-lxml
%if 0%{?rhel} >= 6 || 0%{?fedora}
# some client commands use requests, they are unsupported on RHEL5
Requires:       python-requests
%endif
Requires:       libxslt-python
%if !(0%{?rhel} >= 6 || 0%{?fedora} >= 14)
Requires:       python-simplejson
%endif
Requires:       libxml2-python
Requires:       python-prettytable
Requires:       python-jinja2
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
Requires:       crontabs
Requires:       mod_wsgi
Requires:       python-tgexpandingformwidget
Requires:       httpd
Requires:       python-krbV
Requires:       %{name} = %{version}-%{release}
Requires:       python-TurboMail >= 3.0
Requires:       createrepo
Requires:       yum-utils
Requires:       cracklib-python
Requires:       python-jinja2
Requires:       python-netaddr
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       ovirt-engine-sdk
Requires:       python-itsdangerous
Requires:       python-decorator
Requires:       python-flask
Requires:       python-markdown
Requires:       python-webassets
Requires:       python-passlib
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
Requires:       crontabs
Requires:       httpd
%ifarch %{ix86} x86_64
Requires:       syslinux
%endif
Requires:       yum-utils
Requires:       fence-agents
Requires:       ipmitool
Requires:       wsmancli
Requires:       telnet
Requires:       sudo
Requires:       python-cpio
Requires:       %{name} = %{version}-%{release}
Requires:       python-setuptools
Requires:       python-xmltramp
Requires:       python-krbV
Requires:       python-gevent >= 1.0
Requires:       python-daemon
Requires:       python-werkzeug
Requires:       python-flask
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
Provides:       beaker-redhat-support-addDistro <= 0.19
Obsoletes:      beaker-redhat-support-addDistro <= 0.19
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
tar -C Server/assets/bootstrap --strip-components=1 -xzf %{SOURCE1}
tar -C Server/assets/font-awesome --strip-components=1 -xzf %{SOURCE2}
tar -C Server/assets/typeahead.js --strip-components=1 -xzf %{SOURCE3}
tar -C Server/assets/underscore --strip-components=1 -xzf %{SOURCE4}
tar -C Server/assets/backbone --strip-components=1 -xzf %{SOURCE5}

%build
make \
    %{?with_server:WITH_SERVER=1} \
    %{?with_labcontroller:WITH_LABCONTROLLER=1} \
    %{?with_inttests:WITH_INTTESTS=1}

%install
DESTDIR=%{buildroot} make \
    %{?with_server:WITH_SERVER=1} \
    %{?with_labcontroller:WITH_LABCONTROLLER=1} \
    %{?with_inttests:WITH_INTTESTS=1} \
    install


%check
make \
    %{?with_server:WITH_SERVER=1} \
    %{?with_labcontroller:WITH_LABCONTROLLER=1} \
    %{?with_inttests:WITH_INTTESTS=1} \
    check

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
%dir %{python2_sitelib}/bkr/
%{python2_sitelib}/bkr/__init__.py*
%{python2_sitelib}/bkr/timeout_xmlrpclib.py*
%{python2_sitelib}/bkr/common/
%{python2_sitelib}/bkr/log.py*
%{python2_sitelib}/bkr-*.egg-info/
%doc COPYING

%if %{with server}
%files server
%defattr(-,root,root,-)
%dir %{_sysconfdir}/beaker
%doc documentation/_build/text/whats-new/
%{python2_sitelib}/bkr/server/
%{python2_sitelib}/bkr.server-*-nspkg.pth
%{python2_sitelib}/bkr.server-*.egg-info/
%{_bindir}/%{name}-init
%{_bindir}/nag-mail
%{_bindir}/beaker-log-delete
%{_bindir}/log-delete
%{_bindir}/beaker-check
%{_bindir}/product-update
%{_bindir}/beaker-repo-update
%{_bindir}/beaker-sync-tasks
%{_bindir}/beaker-refresh-ldap
%{_bindir}/beaker-create-kickstart
%{_mandir}/man1/beaker-create-kickstart.1.gz

%if %{with_systemd}
%{_unitdir}/beakerd.service
%attr(0644,apache,apache) %{_tmpfilesdir}/beaker-server.conf
%else
%{_sysconfdir}/init.d/%{name}d
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}
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
%attr(-,apache,root) %dir %{_localstatedir}/lib/%{name}
%endif

%if %{with inttests}
%files integration-tests
%defattr(-,root,root,-)
%{python2_sitelib}/bkr/inttest/
%{python2_sitelib}/bkr.inttest-*-nspkg.pth
%{python2_sitelib}/bkr.inttest-*.egg-info/
%endif

%files client
%defattr(-,root,root,-)
%dir %{_sysconfdir}/beaker
%doc Client/client.conf.example
%{python2_sitelib}/bkr/client/
%{python2_sitelib}/bkr.client-*-nspkg.pth
%{python2_sitelib}/bkr.client-*.egg-info/
%{_bindir}/beaker-wizard
%{_bindir}/bkr
%{_mandir}/man1/beaker-wizard.1.gz
%{_mandir}/man1/bkr.1.gz
%{_mandir}/man1/bkr-*.1.gz
%if 0%{?fedora} >= 17 || 0%{?rhel} >= 7
%{_datadir}/bash-completion
# Server isn't packaged on RHEL7, so tell rpm to ignore this file
%exclude %{_mandir}/man1/beaker-create-kickstart.1.gz
%else
%{_sysconfdir}/bash_completion.d
%endif

%if %{with labcontroller}
%files lab-controller
%defattr(-,root,root,-)
%dir %{_sysconfdir}/beaker
%config(noreplace) %{_sysconfdir}/beaker/labcontroller.conf
%{_sysconfdir}/beaker/power-scripts/
%{_sysconfdir}/beaker/install-failure-patterns/
%{python2_sitelib}/bkr/labcontroller/
%{python2_sitelib}/bkr.labcontroller-*-nspkg.pth
%{python2_sitelib}/bkr.labcontroller-*.egg-info/
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
%{_tmpfilesdir}/beaker-lab-controller.conf
%else
%{_sysconfdir}/init.d/%{name}-proxy
%{_sysconfdir}/init.d/%{name}-watchdog
%{_sysconfdir}/init.d/%{name}-transfer
%{_sysconfdir}/init.d/%{name}-provision
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}-lab-controller
%endif

%attr(0440,root,root) %config(noreplace) %{_sysconfdir}/sudoers.d/%{name}_proxy_clear_netboot
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-lab-controller.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker

%files lab-controller-addDistro
%defattr(-,root,root,-)
%{_var}/lib/beaker/addDistro.sh
%{_var}/lib/beaker/addDistro.d/*
%endif

%changelog
