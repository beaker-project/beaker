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
%global upstream_version 0.18.1

Name:           beaker
Version:        0.18.1
Release:        1%{?dist}
Summary:        Full-stack software and hardware integration testing system
Group:          Applications/Internet
License:        GPLv2+ and BSD
URL:            https://beaker-project.org/

Source0:        https://beaker-project.org/releases/%{name}-%{upstream_version}.tar.gz
# Third-party JS/CSS libraries which are built into Beaker's generated JS/CSS
# (these are submodules in Beaker's git tree, the commit hashes here should
# correspond to the submodule commits)
Source1:        https://github.com/twbs/bootstrap/archive/d9b502dfb876c40b0735008bac18049c7ee7b6d2/bootstrap-d9b502dfb876c40b0735008bac18049c7ee7b6d2.tar.gz
Source2:        https://github.com/FortAwesome/Font-Awesome/archive/b1a8ad47303509e70e56079396fad2afadfd96d5/font-awesome-b1a8ad47303509e70e56079396fad2afadfd96d5.tar.gz
Source3:        https://github.com/twitter/typeahead.js/archive/2bd1119ecdd5ed4bb6b78c83b904d70adc49e023/typeahead.js-2bd1119ecdd5ed4bb6b78c83b904d70adc49e023.tar.gz
Source4:        https://github.com/jashkenas/underscore/archive/edbf2952c2b71f81c6449aef384bdf233a0d63bc/underscore-edbf2952c2b71f81c6449aef384bdf233a0d63bc.tar.gz
Source5:        https://github.com/jashkenas/backbone/archive/53f77901a4ea9c7cf75d3db93ddddf491998d90f/backbone-53f77901a4ea9c7cf75d3db93ddddf491998d90f.tar.gz
Source6:        https://github.com/moment/moment/archive/604c7942de38749e768ff8e327301ea6917c7c73/moment-604c7942de38749e768ff8e327301ea6917c7c73.tar.gz
Source7:        https://github.com/silviomoreto/bootstrap-select/archive/c0c90090e5abeb5c10291430ae2a1778371f5630/bootstrap-select-c0c90090e5abeb5c10291430ae2a1778371f5630.tar.gz
Source8:        https://github.com/wyuenho/backgrid/archive/ff4b033d6f33b3af543e735869b225f4ac984acf/backgrid-ff4b033d6f33b3af543e735869b225f4ac984acf.tar.gz
Source9:        https://github.com/wyuenho/backbone-pageable/archive/61912d577bb5289a80654e89deeb8dc505f283bd/backbone-pageable-61912d577bb5289a80654e89deeb8dc505f283bd.tar.gz
Source10:        https://github.com/medialize/URI.js/archive/40a89137c5bc297f73467290c39ca596f891dcb9/URI.js-40a89137c5bc297f73467290c39ca596f891dcb9.tar.gz
Source11:        https://github.com/makeusabrew/bootbox/archive/a557eb187a72ab375ef34970f4f231739de2b40d/bootbox-a557eb187a72ab375ef34970f4f231739de2b40d.tar.gz
Source12:        https://github.com/ifightcrime/bootstrap-growl/archive/eba6d7685c842f83764290c9ab5e82f7d4ffea22/bootstrap-growl-eba6d7685c842f83764290c9ab5e82f7d4ffea22.tar.gz

BuildRoot:      %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
BuildArch:      noarch
BuildRequires:  make
BuildRequires:  python-setuptools
BuildRequires:  python-nose >= 0.10
BuildRequires:  python-unittest2
# pylint only understands namespace packages since 1.0
BuildRequires:  pylint >= 1.0
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
BuildRequires:  python-keystoneclient
BuildRequires:  python-novaclient
BuildRequires:  python-glanceclient
BuildRequires:  ipxe-bootimgs
BuildRequires:  syslinux
BuildRequires:  dosfstools
BuildRequires:  mtools
BuildRequires:  python-itsdangerous
BuildRequires:  python-decorator
BuildRequires:  python-webassets
BuildRequires:  python-flask
BuildRequires:  python-markdown
BuildRequires:  python-passlib
%if %{with_systemd}
BuildRequires:  systemd
%endif

%endif

%if %{with labcontroller}
# These LC dependencies are needed in build due to tests
BuildRequires:  python-gevent >= 1.0
%endif

# As above, these client dependencies are needed in build because of sphinx
BuildRequires:  python-krbV
BuildRequires:  python-lxml
BuildRequires:  libxslt-python


%package common
Summary:        Common components for Beaker packages
Group:          Applications/Internet
Provides:       %{name} = %{version}-%{release}
Obsoletes:      %{name} < 0.17.0-1


%package client
Summary:        Command-line client for interacting with Beaker
Group:          Applications/Internet
Requires:       python
Requires:       python-setuptools
Requires:       %{name}-common = %{version}-%{release}
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
Summary:        Beaker scheduler and web interface
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
Requires:       %{name}-common = %{version}-%{release}
Requires:       python-TurboMail >= 3.0
Requires:       createrepo
Requires:       yum-utils
Requires:       cracklib-python
Requires:       python-jinja2
Requires:       python-netaddr
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       python-keystoneclient
Requires:       python-novaclient
Requires:       python-glanceclient
Requires:       ipxe-bootimgs
Requires:       syslinux
Requires:       dosfstools
Requires:       mtools
Requires:       python-itsdangerous
Requires:       python-decorator
Requires:       python-flask
Requires:       python-markdown
Requires:       python-webassets
Requires:       /usr/bin/lessc
Requires:       /usr/bin/cssmin
Requires:       /usr/bin/uglifyjs
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
Requires:       %{name}-common = %{version}-%{release}
Requires:       %{name}-server = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       python-nose >= 0.10
Requires:       selenium-python >= 2.12
Requires:       Xvfb
Requires:       firefox
Requires:       lsof
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       openldap-servers
Requires:       python-unittest2
Requires:       python-gunicorn
Requires:       python-mock
%endif


%if %{with labcontroller}
%package lab-controller
Summary:        Daemons for controlling a Beaker lab
Group:          Applications/Internet
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
Requires:       %{name}-common = %{version}-%{release}
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
Summary:        Optional hooks for distro import on Beaker lab controllers
Group:          Applications/Internet
Requires:       %{name}-common = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}
%endif

%description
Beaker is a full stack software and hardware integration testing system, with 
the ability to manage a globally distributed network of test labs.

%description common
Python modules which are used by other Beaker packages.

%description client
The bkr client is a command-line tool for interacting with Beaker servers. You 
can use it to submit Beaker jobs, fetch results, and perform many other tasks.

%if %{with server}
%description server
This package provides the central server components for Beaker, which 
consist of:
* a Python web application, providing services to remote lab controllers as 
  well as a web interface for Beaker users; 
* the beakerd scheduling daemon, which schedules recipes on systems; and 
* command-line tools for managing a Beaker installation.
%endif

%if %{with inttests}
%description integration-tests
This package contains integration tests for Beaker, which require a running 
database and Beaker server.
%endif

%if %{with labcontroller}
%description lab-controller
The lab controller daemons connect to a central Beaker server in order to 
manage a local lab of test systems.

The daemons and associated lab controller tools:
* set up netboot configuration files
* control power for test systems
* collect logs and results from test runs
* track distros available from the lab's local mirror

%description lab-controller-addDistro
addDistro.sh can be called after distros have been imported into Beaker. You 
can install this on your lab controller to automatically launch jobs against 
newly imported distros.
%endif

%prep
%setup -q -n %{name}-%{upstream_version}
tar -C Server/assets/bootstrap --strip-components=1 -xzf %{SOURCE1}
tar -C Server/assets/font-awesome --strip-components=1 -xzf %{SOURCE2}
tar -C Server/assets/typeahead.js --strip-components=1 -xzf %{SOURCE3}
tar -C Server/assets/underscore --strip-components=1 -xzf %{SOURCE4}
tar -C Server/assets/backbone --strip-components=1 -xzf %{SOURCE5}
tar -C Server/assets/moment --strip-components=1 -xzf %{SOURCE6}
tar -C Server/assets/bootstrap-select --strip-components=1 -xzf %{SOURCE7}
tar -C Server/assets/backgrid --strip-components=1 -xzf %{SOURCE8}
tar -C Server/assets/backbone-pageable --strip-components=1 -xzf %{SOURCE9}
tar -C Server/assets/URI.js --strip-components=1 -xzf %{SOURCE10}
tar -C Server/assets/bootbox --strip-components=1 -xzf %{SOURCE11}
tar -C Server/assets/bootstrap-growl --strip-components=1 -xzf %{SOURCE12}

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

%if %{with server}
# Newer RPM fails if site.less doesn't exist, even though it's marked %%ghost 
# and therefore is not included in the RPM. Seems like an RPM bug...
ln -s /dev/null %{buildroot}%{_datadir}/bkr/server/assets/site.less
%endif

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
# Create symlink for site.less (this is ghosted so that other packages can overwrite it)
if [ ! -f %{_datadir}/bkr/server/assets/site.less ] ; then
    ln -s /dev/null %{_datadir}/bkr/server/assets/site.less || :
fi
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

%files common
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
%dir %{_sysconfdir}/%{name}
%doc documentation/_build/text/whats-new/
%{python2_sitelib}/bkr/server/
%{python2_sitelib}/bkr.server-*-nspkg.pth
%{python2_sitelib}/bkr.server-*.egg-info/
%{_bindir}/beaker-init
%{_bindir}/beaker-usage-reminder
%{_bindir}/beaker-log-delete
%{_bindir}/log-delete
%{_bindir}/beaker-check
%{_bindir}/product-update
%{_bindir}/beaker-repo-update
%{_bindir}/beaker-sync-tasks
%{_bindir}/beaker-refresh-ldap
%{_bindir}/beaker-create-kickstart
%{_bindir}/beaker-create-ipxe-image
%{_mandir}/man8/beaker-create-ipxe-image.8.gz
%{_mandir}/man8/beaker-create-kickstart.8.gz
%{_mandir}/man8/beaker-repo-update.8.gz
%{_mandir}/man8/beaker-usage-reminder.8.gz

%if %{with_systemd}
%{_unitdir}/beakerd.service
%attr(0644,apache,apache) %{_tmpfilesdir}/beaker-server.conf
%else
%{_sysconfdir}/init.d/beakerd
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}
%endif

%config(noreplace) %{_sysconfdir}/cron.d/%{name}
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-server.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker
%attr(0755,root,root)%{_bindir}/beakerd
%config(noreplace) %{_sysconfdir}/httpd/conf.d/beaker-server.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/beaker-server.wsgi
%attr(-,apache,root) %{_datadir}/bkr/server
%ghost %attr(0777,root,root) %{_datadir}/bkr/server/assets/site.less
%attr(0660,apache,root) %config(noreplace) %{_sysconfdir}/%{name}/server.cfg
%dir %{_localstatedir}/log/%{name}
%dir %{_localstatedir}/cache/%{name}
%attr(-,apache,root) %dir %{_localstatedir}/cache/%{name}/assets
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/logs
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/rpms
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/repos
%attr(-,apache,root) %dir %{_localstatedir}/lib/%{name}
%else
# If we're not building the -server subpackage we need to tell RPM to ignore 
# the server man pages. They will always be present because the docs build 
# always installs them all.
%exclude %{_mandir}/man8/beaker-create-ipxe-image.8.gz
%exclude %{_mandir}/man8/beaker-create-kickstart.8.gz
%exclude %{_mandir}/man8/beaker-repo-update.8.gz
%exclude %{_mandir}/man8/beaker-usage-reminder.8.gz
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
%dir %{_sysconfdir}/%{name}
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
%else
%{_sysconfdir}/bash_completion.d
%endif

%if %{with labcontroller}
%files lab-controller
%defattr(-,root,root,-)
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/labcontroller.conf
%{_sysconfdir}/%{name}/power-scripts/
%{_sysconfdir}/%{name}/install-failure-patterns/
%{python2_sitelib}/bkr/labcontroller/
%{python2_sitelib}/bkr.labcontroller-*-nspkg.pth
%{python2_sitelib}/bkr.labcontroller-*.egg-info/
%{_bindir}/beaker-proxy
%{_bindir}/beaker-watchdog
%{_bindir}/beaker-transfer
%{_bindir}/beaker-import
%{_bindir}/beaker-provision
%{_bindir}/beaker-pxemenu
%{_bindir}/beaker-expire-distros
%{_bindir}/beaker-clear-netboot
%config(noreplace) %{_sysconfdir}/httpd/conf.d/beaker-lab-controller.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/lab-controller
%config(noreplace) %{_sysconfdir}/cron.hourly/beaker_expire_distros
%attr(-,apache,root) %dir %{_var}/www/%{name}
%attr(-,apache,root) %dir %{_var}/www/%{name}/logs
%dir %{_localstatedir}/log/%{name}

%if %{with_systemd}
%{_unitdir}/beaker-proxy.service
%{_unitdir}/beaker-provision.service
%{_unitdir}/beaker-watchdog.service
%{_unitdir}/beaker-transfer.service
%{_tmpfilesdir}/beaker-lab-controller.conf
%else
%{_sysconfdir}/init.d/beaker-proxy
%{_sysconfdir}/init.d/beaker-watchdog
%{_sysconfdir}/init.d/beaker-transfer
%{_sysconfdir}/init.d/beaker-provision
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}-lab-controller
%endif

%attr(0440,root,root) %config(noreplace) %{_sysconfdir}/sudoers.d/beaker_proxy_clear_netboot
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-lab-controller.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker

%files lab-controller-addDistro
%defattr(-,root,root,-)
%{_var}/lib/%{name}/addDistro.sh
%{_var}/lib/%{name}/addDistro.d/*
%endif

%changelog
