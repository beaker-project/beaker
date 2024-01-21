%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%endif

%if 0%{?fedora} >= 30 || 0%{?rhel} >= 8
%bcond_without python3
%else
%bcond_with python3
%endif

%global _lc_services beaker-proxy beaker-provision beaker-watchdog beaker-transfer

# This will not necessarily match the RPM Version if the real version number is
# not representable in RPM. For example, a release candidate might be 0.15.0rc1
# but that is not usable for the RPM Version because it sorts higher than
# 0.15.0, so the RPM will have Version 0.15.0 and Release 0.rc1 in that case.
%global upstream_version 29.1

Name:           beaker
Version:        29.1
Release:        1%{?dist}
Summary:        Full-stack software and hardware integration testing system
Group:          Applications/Internet
License:        GPLv2+ and BSD
URL:            https://beaker-project.org/

Source0:        https://github.com/beaker-project/beaker/archive/%{name}-%{upstream_version}.tar.gz
# Third-party JS/CSS libraries which are built into Beaker's generated JS/CSS
# (these are submodules in Beaker's git tree, the commit hashes here should
# correspond to the submodule commits)
Source1:        https://github.com/twbs/bootstrap/archive/d9b502dfb876c40b0735008bac18049c7ee7b6d2/bootstrap-d9b502dfb876c40b0735008bac18049c7ee7b6d2.tar.gz
Source2:        https://github.com/FortAwesome/Font-Awesome/archive/a8386aae19e200ddb0f6845b5feeee5eb7013687/font-awesome-a8386aae19e200ddb0f6845b5feeee5eb7013687.tar.gz
Source3:        https://github.com/twitter/typeahead.js/archive/2bd1119ecdd5ed4bb6b78c83b904d70adc49e023/typeahead.js-2bd1119ecdd5ed4bb6b78c83b904d70adc49e023.tar.gz
Source4:        https://github.com/jashkenas/underscore/archive/edbf2952c2b71f81c6449aef384bdf233a0d63bc/underscore-edbf2952c2b71f81c6449aef384bdf233a0d63bc.tar.gz
Source5:        https://github.com/jashkenas/backbone/archive/53f77901a4ea9c7cf75d3db93ddddf491998d90f/backbone-53f77901a4ea9c7cf75d3db93ddddf491998d90f.tar.gz
Source6:        https://github.com/moment/moment/archive/604c7942de38749e768ff8e327301ea6917c7c73/moment-604c7942de38749e768ff8e327301ea6917c7c73.tar.gz
Source7:        https://github.com/silviomoreto/bootstrap-select/archive/005d84efe1679d3c83f02bcd4a8cc5f89d500afc/bootstrap-select-005d84efe1679d3c83f02bcd4a8cc5f89d500afc.tar.gz
Source8:        https://github.com/wyuenho/backgrid/archive/ff4b033d6f33b3af543e735869b225f4ac984acf/backgrid-ff4b033d6f33b3af543e735869b225f4ac984acf.tar.gz
Source9:        https://github.com/wyuenho/backbone-pageable/archive/61912d577bb5289a80654e89deeb8dc505f283bd/backbone-pageable-61912d577bb5289a80654e89deeb8dc505f283bd.tar.gz
Source10:        https://github.com/medialize/URI.js/archive/40a89137c5bc297f73467290c39ca596f891dcb9/URI.js-40a89137c5bc297f73467290c39ca596f891dcb9.tar.gz
Source11:        https://github.com/makeusabrew/bootbox/archive/ed5c62a02ab1eb512c38f4be1d0f6774c51a85c6/bootbox-ed5c62a02ab1eb512c38f4be1d0f6774c51a85c6.tar.gz
Source12:        https://github.com/ifightcrime/bootstrap-growl/archive/eba6d7685c842f83764290c9ab5e82f7d4ffea22/bootstrap-growl-eba6d7685c842f83764290c9ab5e82f7d4ffea22.tar.gz
Source13:       https://github.com/eternicode/bootstrap-datepicker/archive/b374f23971817d507bded0dc16892e87a6d2fe42/bootstrap-datepicker-b374f23971817d507bded0dc16892e87a6d2fe42.tar.gz
Source14:       https://github.com/chjj/marked/archive/2b5802f258c5e23e48366f2377fbb4c807f47658/marked-2b5802f258c5e23e48366f2377fbb4c807f47658.tar.gz
Source15:       https://github.com/jsmreese/moment-duration-format/archive/8d0bf29a1eab180cb83d0f13f93f6974faedeafd/moment-duration-format-8d0bf29a1eab180cb83d0f13f93f6974faedeafd.tar.gz

BuildArch:      noarch
BuildRequires:  make
%if %{with python3}
BuildRequires:  python3-setuptools
BuildRequires:  python3-pytest
BuildRequires:  python3-devel
BuildRequires:  python3-docutils
BuildRequires:  python3-sphinx
BuildRequires:  python3-six
%else
BuildRequires:  python-setuptools
BuildRequires:  python-nose >= 0.10
BuildRequires:  python-mock
BuildRequires:  python2-devel
BuildRequires:  python-docutils >= 0.6
BuildRequires:  python-sphinx >= 1.0
BuildRequires:  python-sphinxcontrib-httpdomain
%endif

%package common
Summary:        Common components for Beaker packages
Group:          Applications/Internet
Provides:       %{name} = %{version}-%{release}
Obsoletes:      %{name} < 0.17.0-1

%package client
Summary:        Command-line client for interacting with Beaker
Group:          Applications/Internet
Requires:       %{name}-common = %{version}-%{release}
# setup.py uses pkg-config to find the right installation paths
BuildRequires:  pkgconfig(bash-completion)
%if %{with python3}
# These client dependencies are needed in build because of sphinx
BuildRequires:  python3-gssapi
BuildRequires:  python3-lxml
BuildRequires:  python3-prettytable
BuildRequires:  python3-libxml2
Requires:       python3-six
Requires:       python3-setuptools
Requires:       python3-gssapi
Requires:       python3-lxml
Requires:       python3-requests
Requires:       python3-libxml2
Requires:       python3-prettytable
Requires:       python3-jinja2
%else
# old style Python package names
# These client dependencies are needed in build because of sphinx
BuildRequires:  python-gssapi
BuildRequires:  python-lxml
BuildRequires:  libxslt-python
BuildRequires:  python-prettytable
Requires:       python-six
Requires:       python
Requires:       python-setuptools
Requires:       python-gssapi
Requires:       python-lxml
Requires:       python-requests
Requires:       libxslt-python
Requires:       libxml2-python
Requires:       python-prettytable
Requires:       python-jinja2
%endif
# beaker-wizard was moved from rhts-devel to here in 4.52
Conflicts:      rhts-devel < 4.52

%if %{without python3}
%package server
Summary:        Beaker scheduler and web interface
Group:          Applications/Internet
Requires:       %{name}-common = %{version}-%{release}
BuildRequires:  python-kid
# These runtime dependencies are needed at build time as well, because
# the unit tests and Sphinx autodoc import the server code as part of the
# build process.
BuildRequires:  createrepo_c
BuildRequires:  ipxe-bootimgs
BuildRequires:  syslinux
BuildRequires:  mtools
Requires:       createrepo_c
Requires:       ipxe-bootimgs
Requires:       syslinux
Requires:       mtools
Requires:       intltool
Requires:       crontabs
Requires:       mod_wsgi
Requires:       httpd
Requires:       dnf
Requires:       nodejs-less >= 1.7, nodejs-less <= 2.0
Requires:       /usr/bin/cssmin
Requires:       /usr/bin/uglifyjs
BuildRequires:  python-requests
BuildRequires:  TurboGears >= 1.1.3
BuildRequires:  python-turbojson
BuildRequires:  python-sqlalchemy >= 0.9
BuildRequires:  python-lxml
BuildRequires:  python-ldap
BuildRequires:  python-rdflib >= 3.2.0
BuildRequires:  python-TurboMail >= 3.0
BuildRequires:  python-pwquality
BuildRequires:  rpm-python
BuildRequires:  python-netaddr
BuildRequires:  python-itsdangerous
BuildRequires:  python-decorator
BuildRequires:  python-webassets
BuildRequires:  python-flask
BuildRequires:  python-markdown
BuildRequires:  python-passlib
BuildRequires:  python-alembic
BuildRequires:  python-daemon
BuildRequires:  python-futures
Requires:       TurboGears >= 1.1.3
Requires:       python-turbojson
Requires:       python-sqlalchemy >= 0.9
Requires:       python-decorator
Requires:       python-lxml
Requires:       python-ldap
Requires:       python-rdflib >= 3.2.0
Requires:       python-daemon
Requires:       python-lockfile >= 0.9
Requires:       python-gssapi
Requires:       python-TurboMail >= 3.0
Requires:       python-pwquality
Requires:       python-jinja2
Requires:       python-netaddr
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       python-itsdangerous
Requires:       python-decorator
Requires:       python-flask
Requires:       python-markdown
Requires:       python-webassets
Requires:       python-passlib
Requires:       python-alembic
Requires:       python-futures
BuildRequires:  systemd
BuildRequires:  pkgconfig(systemd)
Requires:       systemd-units
Requires(post): systemd
Requires(pre):  systemd
Requires(postun):  systemd
%endif

%if %{without python3}
%package integration-tests
Summary:        Integration tests for Beaker
Group:          Applications/Internet
Requires:       %{name}-common = %{version}-%{release}
Requires:       %{name}-server = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       Xvfb
Requires:       firefox
Requires:       lsof
Requires:       openldap-servers
Requires:       nss_wrapper
# old style Python package names
Requires:       python-nose >= 0.10
%if 0%{?rhel}
Requires:       selenium-python >= 2.12
%else
Requires:       python-selenium >= 2.12
%endif
Requires:       python-requests >= 1.0
Requires:       python-requests-kerberos
Requires:       python-gunicorn
Requires:       python-mock
# Workaround for https://bugzilla.redhat.com/show_bug.cgi?id=1358533
Requires:       python-cssselect
%endif

%package lab-controller
Summary:           Daemons for controlling a Beaker lab
Group:             Applications/Internet

BuildRequires:     systemd
BuildRequires:     pkgconfig(systemd)

# The build dependencies listed below are not directly required for building the component.
# However, they are included to ensure that all unit tests can be executed during the check macro.
%if %{with python3}
BuildRequires:     python3-gevent
BuildRequires:     python3-lxml
BuildRequires:     python3-werkzeug
BuildRequires:     python3-psutil
BuildRequires:     python3-daemon
%else
# python2-gevent112 is a special build created for labcontroller. It includes backports to ensure compatibility with py2.7.9 SSL backport.
BuildRequires:     python2-gevent112
BuildRequires:     python2-psutil
BuildRequires:     python-lxml
BuildRequires:     python-daemon
%endif

# Syslinux is only available on x86_64. This package is used to provide pxelinux.0, which is then copied to the TFTP directory.
# Removing this package will result in no default boot loader, but conversely will allow multi-arch support.
Requires:          syslinux
Requires:          %{name}-common = %{version}-%{release}
Requires:          crontabs
Requires:          httpd
Requires:          ipmitool
Requires:          wsmancli
Requires:          /usr/bin/virsh
Requires:          telnet
Requires:          dnf
Requires:          sudo
Requires:          systemd-units
Requires(post):    systemd
Requires(pre):     systemd
Requires(postun):  systemd

%if %{with python3}
Requires:          fence-agents-all
Requires:          python3
Requires:          python3-cpio
Requires:          python3-daemon
Requires:          python3-flask
Requires:          python3-gssapi
Requires:          python3-lxml
Requires:          python3-setuptools
Requires:          python3-werkzeug
Requires:          python3-gevent
%else
Requires:          fence-agents
Requires:          python
Requires:          python-cpio
Requires:          python-daemon
Requires:          python-flask
Requires:          python-gssapi
Requires:          python-lxml
Requires:          python-setuptools
Requires:          python-werkzeug
Requires:          python2-gevent112
%endif

%package lab-controller-addDistro
Summary:        Optional hooks for distro import on Beaker lab controllers
Group:          Applications/Internet
Requires:       %{name}-common = %{version}-%{release}
Requires:       %{name}-lab-controller = %{version}-%{release}
Requires:       %{name}-client = %{version}-%{release}


%description
Beaker is a full stack software and hardware integration testing system, with
the ability to manage a globally distributed network of test labs.

%description common
Python modules which are used by other Beaker packages.

%description client
The bkr client is a command-line tool for interacting with Beaker servers. You
can use it to submit Beaker jobs, fetch results, and perform many other tasks.

%if %{without python3}
%description server
This package provides the central server components for Beaker, which
consist of:
* a Python web application, providing services to remote lab controllers as
  well as a web interface for Beaker users;
* the beakerd scheduling daemon, which schedules recipes on systems; and
* command-line tools for managing a Beaker installation.
%endif

%if %{without python3}
%description integration-tests
This package contains integration tests for Beaker, which require a running
database and Beaker server.
%endif

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

%prep
%setup -q -n %{name}-%{name}-%{upstream_version}
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
tar -C Server/assets/bootstrap-datepicker --strip-components=1 -xzf %{SOURCE13}
tar -C Server/assets/marked --strip-components=1 -xzf %{SOURCE14}
tar -C Server/assets/moment-duration-format --strip-components=1 -xzf %{SOURCE15}

%build
export BKR_PY3=%{with python3}
make

%install
# RHEL 8 python3-nose removed unversioned executables
%if 0%{?rhel} >= 8
ln -sf %{_bindir}/nosetests-%{python3_version} %{buildroot}/nosetests-3
%endif

export BKR_PY3=%{with python3}
DESTDIR=%{buildroot} make install

%if %{without python3}
# Newer RPM fails if site.less doesn't exist, even though it's marked %%ghost
# and therefore is not included in the RPM. Seems like an RPM bug...
ln -s /dev/null %{buildroot}%{_datadir}/bkr/server/assets/site.less
%else
install -m0755 -d %{buildroot}/%{_localstatedir}/log/%{name}
install -m0755 -d %{buildroot}/%{_sysconfdir}/logrotate.d
install -m0644 Server/logrotate.d/beaker %{buildroot}/%{_sysconfdir}/logrotate.d/beaker
%endif

%check
%if 0%{?rhel} >= 8
export PATH=%{buildroot}:$PATH
%endif
export BKR_PY3=%{with python3}
make check
%if 0%{?rhel} >= 8
unlink %{buildroot}/nosetests-3
%endif

%if %{without python3}
%post server
%systemd_post beakerd.service

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

%post lab-controller
%systemd_post %{_lc_services}

# Migrate ConcurrentLogHandler -> syslog
rm -f %{_localstatedir}/log/%{name}/*.lock >/dev/null 2>&1 || :
chown root:root %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
chmod go-w %{_localstatedir}/log/%{name}/*.log >/dev/null 2>&1 || :
# Restart rsyslog so that it notices the config which we ship
/sbin/service rsyslog condrestart >/dev/null 2>&1 || :

%if %{without python3}
%postun server
%systemd_postun_with_restart beakerd.service
%endif

%postun lab-controller
%systemd_postun_with_restart %{_lc_services}

%if %{without python3}
%preun server
%systemd_preun beakerd.service
%endif

%preun lab-controller
%systemd_preun %{_lc_services}

%files common
%if %{with python3}
%dir %{python3_sitelib}/bkr/
%{python3_sitelib}/bkr/__init__.py*
%{python3_sitelib}/bkr/common/
%{python3_sitelib}/bkr/log.py*
%{python3_sitelib}/bkr/__pycache__/*
%{python3_sitelib}/%{name}_common-*.egg-info/
%else
%dir %{python2_sitelib}/bkr/
%{python2_sitelib}/bkr/__init__.py*
%{python2_sitelib}/bkr/common/
%{python2_sitelib}/bkr/log.py*
%{python2_sitelib}/beaker_common-*.egg-info/
%endif
%doc COPYING

%if %{without python3}
%files server
%dir %{_sysconfdir}/%{name}
%doc documentation/_build/text/whats-new/
%{python2_sitelib}/bkr/server/
%{python2_sitelib}/beaker_server-*-nspkg.pth
%{python2_sitelib}/beaker_server-*.egg-info/
%{_bindir}/beaker-init
%{_bindir}/beaker-usage-reminder
%{_bindir}/beaker-log-delete
%{_bindir}/product-update
%{_bindir}/beaker-repo-update
%{_bindir}/beaker-sync-tasks
%{_bindir}/beaker-refresh-ldap
%{_bindir}/beaker-create-kickstart
%{_bindir}/beaker-create-ipxe-image
%{_mandir}/man8/beaker-create-ipxe-image.8.gz
%{_mandir}/man8/beaker-create-kickstart.8.gz
%{_mandir}/man8/beaker-init.8.gz
%{_mandir}/man8/beaker-repo-update.8.gz
%{_mandir}/man8/beaker-usage-reminder.8.gz

%{_unitdir}/beakerd.service
%attr(0644,apache,apache) %{_tmpfilesdir}/beaker-server.conf
%attr(-,apache,root) %dir /run/%{name}

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
%endif

%if %{without python3}
%files integration-tests
%{python2_sitelib}/bkr/inttest/
%{python2_sitelib}/beaker_integration_tests-*-nspkg.pth
%{python2_sitelib}/beaker_integration_tests-*.egg-info/
%{_datadir}/beaker-integration-tests
%endif

%files client
%dir %{_sysconfdir}/%{name}
%doc Client/client.conf.example
%if %{with python3}
%{python3_sitelib}/bkr/client/
%{python3_sitelib}/%{name}_client-*-nspkg.pth
%{python3_sitelib}/%{name}_client-*.egg-info/
%else
%{python2_sitelib}/bkr/client/
%{python2_sitelib}/beaker_client-*-nspkg.pth
%{python2_sitelib}/beaker_client-*.egg-info/
%endif
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

%files lab-controller
%dir %{_sysconfdir}/%{name}
%config(noreplace) %{_sysconfdir}/%{name}/labcontroller.conf
%{_sysconfdir}/%{name}/power-scripts/
%{_sysconfdir}/%{name}/install-failure-patterns/
%{_bindir}/beaker-proxy
%{_bindir}/beaker-watchdog
%{_bindir}/beaker-transfer
%{_bindir}/beaker-import
%{_bindir}/beaker-provision
%{_bindir}/beaker-pxemenu
%{_bindir}/beaker-expire-distros
%{_bindir}/beaker-clear-netboot
%{_mandir}/man8/beaker-import.8.gz
%config(noreplace) %{_sysconfdir}/httpd/conf.d/beaker-lab-controller.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/lab-controller
%config(noreplace) %{_sysconfdir}/cron.hourly/beaker_expire_distros
%attr(-,apache,root) %dir %{_var}/www/%{name}
%attr(-,apache,root) %dir %{_var}/www/%{name}/logs
%dir %{_localstatedir}/log/%{name}

%{_unitdir}/beaker-proxy.service
%{_unitdir}/beaker-provision.service
%{_unitdir}/beaker-watchdog.service
%{_unitdir}/beaker-transfer.service
%{_tmpfilesdir}/beaker-lab-controller.conf
%attr(-,apache,root) %dir /run/%{name}-lab-controller

%attr(0440,root,root) %config(noreplace) %{_sysconfdir}/sudoers.d/beaker_proxy_clear_netboot
%config(noreplace) %{_sysconfdir}/rsyslog.d/beaker-lab-controller.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/beaker

%if %{with python3}
%{python3_sitelib}/bkr/labcontroller/
%{python3_sitelib}/beaker_lab_controller-*-nspkg.pth
%{python3_sitelib}/beaker_lab_controller-*.egg-info/
%else
%{python2_sitelib}/bkr/labcontroller/
%{python2_sitelib}/beaker_lab_controller-*-nspkg.pth
%{python2_sitelib}/beaker_lab_controller-*.egg-info/
%endif

%files lab-controller-addDistro
%{_var}/lib/%{name}/addDistro.sh
%{_var}/lib/%{name}/addDistro.d/*

%changelog
