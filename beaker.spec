%{!?python_sitelib: %global python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}
%{!?pyver: %global pyver %(%{__python} -c "import sys ; print sys.version[:3]")}

# The server, lab controller, and integration test subpackages can be conditionally built.
# They are only enabled on RHEL 6 (for now).
# Use rpmbuild --with/--without to override.
%if 0%{?rhel} == 6
%bcond_without server
%bcond_without labcontroller
%bcond_without inttests
%else
%bcond_with server
%bcond_with labcontroller
%bcond_with inttests
%endif

# Note: While some parts of this file use "%{name}, "beaker" is still
# hardcoded in a lot of places, both here and in the source code
Name:           beaker
Version:        0.11.2
Release:        1%{?dist}
Summary:        Filesystem layout for Beaker
Group:          Applications/Internet
License:        GPLv2+
URL:            http://beaker-project.org/
Source0:        http://beaker-project.org/releases/%{name}-%{version}.tar.gz
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
BuildRequires:  bash-completion

%if %{with server}
BuildRequires:  python-kid
# These server dependencies are needed in the build, because
# sphinx imports bkr.server modules to generate API docs
BuildRequires:  TurboGears >= 1.1.3
BuildRequires:  python-sqlalchemy >= 0.6
BuildRequires:  python-xmltramp
BuildRequires:  python-lxml
BuildRequires:  python-ldap
BuildRequires:  python-TurboMail >= 3.0
BuildRequires:  cracklib-python
BuildRequires:  python-concurrentloghandler
BuildRequires:  rpm-python
BuildRequires:  rhts-python
BuildRequires:  python-netaddr
BuildRequires:  ovirt-engine-sdk
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
Requires:       python-concurrentloghandler
Requires:       rhts-python
Requires:       cracklib-python
Requires:       python-jinja2
Requires:       python-netaddr
# Kerberos support was added to requests in 0.13.4
Requires:       python-requests >= 0.13.4
Requires:       ovirt-engine-sdk
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
Requires:       python-requests >= 0.11
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
Requires:       telnet
Requires:       sudo
Requires:       python-cpio
Requires:	%{name} = %{version}-%{release}
Requires:       kobo >= 0.3.2
Requires:	kobo-client
Requires:	python-setuptools
Requires:	python-xmltramp
Requires:       python-krbV
Requires:       python-concurrentloghandler
Requires:       python-gevent >= 1.0
Requires:       python-daemon

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
%setup -q

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

%clean
%{__rm} -rf %{buildroot}

%if %{with server}
%post server
/sbin/chkconfig --add beakerd
%endif

%if %{with labcontroller}
%post lab-controller
/sbin/chkconfig --add beaker-proxy
/sbin/chkconfig --add beaker-watchdog
/sbin/chkconfig --add beaker-transfer
/sbin/chkconfig --add beaker-provision
%endif

%if %{with server}
%postun server
if [ "$1" -ge "1" ]; then
        /sbin/service beakerd condrestart >/dev/null 2>&1 || :
fi
%endif

%if %{with labcontroller}
%postun lab-controller
if [ "$1" -ge "1" ]; then
        /sbin/service beaker-proxy condrestart >/dev/null 2>&1 || :
        /sbin/service beaker-watchdog condrestart >/dev/null 2>&1 || :
        /sbin/service beaker-transfer condrestart >/dev/null 2>&1 || :
        /sbin/service beaker-provision condrestart >/dev/null 2>&1 || :
fi
%endif

%if %{with server}
%preun server
if [ "$1" -eq "0" ]; then
        /sbin/service beakerd stop >/dev/null 2>&1 || :
        /sbin/chkconfig --del beakerd || :
fi
%endif

%if %{with labcontroller}
%preun lab-controller
if [ "$1" -eq "0" ]; then
        /sbin/service beaker-proxy stop >/dev/null 2>&1 || :
        /sbin/service beaker-watchdog stop >/dev/null 2>&1 || :
        /sbin/service beaker-transfer stop >/dev/null 2>&1 || :
        /sbin/service beaker-provision stop >/dev/null 2>&1 || :
        /sbin/chkconfig --del beaker-proxy || :
        /sbin/chkconfig --del beaker-watchdog || :
        /sbin/chkconfig --del beaker-transfer || :
        /sbin/chkconfig --del beaker-provision || :
fi
rm -rf %{_var}/lib/beaker/osversion_data
%endif

%files
%defattr(-,root,root,-)
%{python_sitelib}/bkr/__init__.py*
%{python_sitelib}/bkr/timeout_xmlrpclib.py*
%{python_sitelib}/bkr/common/
%{python_sitelib}/bkr/upload.py*
%{python_sitelib}/bkr/log.py*
%{python_sitelib}/bkr-%{version}-*
%{python_sitelib}/bkr-%{version}-py%{pyver}.egg-info/
%doc COPYING

%if %{with server}
%files server
%defattr(-,root,root,-)
%doc Server/README
%doc SchemaUpgrades/upgrade_*
%{python_sitelib}/bkr/server/
%{python_sitelib}/bkr.server-%{version}-*
%{python_sitelib}/bkr.server-%{version}-py%{pyver}.egg-info/
%{_bindir}/start-%{name}
%{_bindir}/%{name}-init
%{_bindir}/nag-mail
%{_bindir}/log-delete
%{_bindir}/beaker-check
%{_bindir}/product-update
%{_bindir}/beaker-repo-update
%{_bindir}/%{name}-cleanup-visits
%{_sysconfdir}/init.d/%{name}d
%config(noreplace) %{_sysconfdir}/cron.d/%{name}
%attr(0755,root,root)%{_bindir}/%{name}d
%config(noreplace) %{_sysconfdir}/httpd/conf.d/%{name}-server.conf
%attr(-,apache,root) %dir %{_datadir}/bkr
%attr(-,apache,root) %{_datadir}/bkr/%{name}-server.wsgi
%attr(-,apache,root) %{_datadir}/bkr/server
%attr(-,apache,root) %config(noreplace) %{_sysconfdir}/%{name}/server.cfg
%attr(-,apache,root) %dir %{_localstatedir}/log/%{name}
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/logs
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/rpms
%attr(-,apache,root) %dir %{_localstatedir}/www/%{name}/repos
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}
%endif

%if %{with inttests}
%files integration-tests
%defattr(-,root,root,-)
%{python_sitelib}/bkr/inttest/
%{python_sitelib}/bkr.inttest-%{version}-*
%{python_sitelib}/bkr.inttest-%{version}-py%{pyver}.egg-info/
%endif

%files client
%defattr(-,root,root,-)
%config(noreplace) %{_sysconfdir}/beaker/client.conf
%{python_sitelib}/bkr/client/
%{python_sitelib}/bkr.client-%{version}-*
%{python_sitelib}/bkr.client-%{version}-py%{pyver}.egg-info/
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
%{python_sitelib}/bkr.labcontroller-%{version}-*
%{python_sitelib}/bkr.labcontroller-%{version}-py%{pyver}.egg-info/
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
%{_sysconfdir}/cron.hourly/beaker_expire_distros
%attr(-,apache,root) %dir %{_var}/www/beaker
%attr(-,apache,root) %dir %{_var}/www/beaker/logs
%attr(-,apache,root) %dir %{_localstatedir}/log/%{name}
%{_sysconfdir}/init.d/%{name}-proxy
%{_sysconfdir}/init.d/%{name}-watchdog
%{_sysconfdir}/init.d/%{name}-transfer
%{_sysconfdir}/init.d/%{name}-provision
%attr(-,apache,root) %dir %{_localstatedir}/run/%{name}-lab-controller
%attr(0440,root,root) %{_sysconfdir}/sudoers.d/%{name}_proxy_clear_netboot

%files lab-controller-addDistro
%defattr(-,root,root,-)
%{_var}/lib/beaker/addDistro.sh
%{_var}/lib/beaker/addDistro.d/*
%endif

%changelog
* Wed Jan 30 2013 Dan Callaghan <dcallagh@redhat.com> 0.11.2-1
- 903893 only reuse MAC addresses once the entire recipe set is finished
  (dcallagh@redhat.com)

* Mon Jan 21 2013 Dan Callaghan <dcallagh@redhat.com> 0.11.1-1
- 896622 ensure Jobs are not added to the session until fully populated 
  (dcallagh@redhat.com)

* Mon Jan 14 2013 Nick Coghlan <ncoghlan@redhat.com> 0.11.0-1
- 875535 fix typos in CPU flag filter (dcallagh@redhat.com)
- 880424 identity.provider should not be set in server config
  (dcallagh@redhat.com)
- 865679 fstype kickstart metadata (dcallagh@redhat.com)
- 865680 linkdelay kickstart metadata variable, for adding LINKDELAY to ifcfg-*
  (dcallagh@redhat.com)
- 869758 exclude repo URLs containing $ from Anaconda (dcallagh@redhat.com)
- 880039 escape shell metachars when writing to /etc/yum.repos.d
  (dcallagh@redhat.com)
- 813574 Lab controller daemons now use python-daemon (dcallagh@redhat.com)
- 881563 upgrade notes to ensure recipe.recipe_set_id and recipe_set.job_id are
  not NULLable (dcallagh@redhat.com)
- 876582 Allow default timezone to be set at each lab (bpeck@redhat.com)
- 865676 Users can now change their passwords (if applicable)
  (rmancy@redhat.com)
- 880899 Declare 'op' attribute as optional (qwan@redhat.com)
- 883214 CPU speed value should be float type in filtering (qwan@redhat.com)
- 872428 Documentation for creating a simple task. (asaha@redhat.com)
- 876752 bkr machine-test should filter out excluded families
  (dcallagh@redhat.com)
- 880853 clean up transaction handling and exception handling in beakerd
  (dcallagh@redhat.com)
- 885554 if oVirt is enabled, don't abort recipes with no candidate systems
  (dcallagh@redhat.com)
- 869455 *really* ensure Jobs are not added to the session until fully
  populated (dcallagh@redhat.com)
- 872001 delete rendered_kickstart rows when recipes are deleted
  (dcallagh@redhat.com)
- 839583 send system utilisation metrics (dcallagh@redhat.com)
- 695986 send system utilisation metrics broken down by arch and lab
  (dcallagh@redhat.com)
- 843854 Clear netboot config files synchronously in %%post
  (ncoghlan@redhat.com)
- 877264 query for reporting user machine hours (dcallagh@redhat.com)
- 877272 query for reporting task durations (dcallagh@redhat.com)
- 873714 per-osmajor install options (dcallagh@redhat.com)
- 883606 External Reports page (rmancy@redhat.com)
- 193142 queries for system reporting (dcallagh@redhat.com)
- 584783 Report recipe statistics to Graphite (ncoghlan@redhat.com)
- 741960 queries for system breakages (dcallagh@redhat.com)
- 591656 Record installation progress of recipe (rmancy@redhat.com)
- 883668 Ensure watchdogs with NULL kill_time are not reported as active
  (rmancy@redhat.com)
- 591656 SQL query for reporting resource install failures (rmancy@redhat.com)
- 591656 SQL reporting query for the duration of an installation
  (rmancy@redhat.com)
- 888673 Do not allow the 'Return' of a system via the WebUI if it's running a
  recipe (rmancy@redhat.com)
- 877274 SQL query for reporting job priority bump by user (rmancy@redhat.com)
- 591656 Measure time between recipe_set enqueue and recipe start
  (rmancy@redhat.com)
- docs: Restructured and updated (Migrated to Sphinx/reStructuredText)
- docs: add missing system content from components.xml (dcallagh@redhat.com)
- docs: merge Installation Guide into Admin and User Guides
  (dcallagh@redhat.com)
- docs: describe supported queries concept in admin guide
  (dcallagh@redhat.com)
- docs: describe Graphite integration in admin guide
  (dcallagh@redhat.com)
- docs: autofs is needed on RHEV hypervisors (dcallagh@redhat.com)
- Emit most bootloader config files for every arch (ncoghlan@redhat.com)
- fix rhts_partitions syntax error with Jinja 2.6 (dcallagh@redhat.com)
- Include recipe ID in install_start log message (ncoghlan@redhat.com)
- Make bootloader configuration less magical (ncoghlan@redhat.com)
- Link to possible systems broken when the Server is installed in a sub-
  directory. (asaha@redhat.com)
- clean up bkr workflow usage message (dcallagh@redhat.com)
- fix a bunch of Unicode type warnings (dcallagh@redhat.com)
- two-argument .join() is not accepted in sqlalchemy 0.7 (dcallagh@redhat.com)
* Thu Dec 20 2012 Dan Callaghan <dcallagh@redhat.com> 0.10.6-1
- 880440 Fix fallback logic for FQDN determination (ncoghlan@redhat.com)

* Mon Dec 03 2012 Dan Callaghan <dcallagh@redhat.com> 0.10.5-2
- 882740 one more fix for guest recipes in 0.10 schema upgrade notes
  (dcallagh@redhat.com)

* Mon Dec 03 2012 Dan Callaghan <dcallagh@redhat.com> 0.10.5-1
- 880852 need to commit in "recipe no longer has access" code path
  (dcallagh@redhat.com)
- 880440 Fall back to config files if 'hostname -f' is dodgy
  (ncoghlan@redhat.com)
- 882740 fix 0.10 schema upgrade notes for guest recipes which are not
  scheduled (dcallagh@redhat.com)
- 882742 fix DetachedInstanceError in log-delete exception handler
  (dcallagh@redhat.com)
- tests: wait for search bar animations to finish (dcallagh@redhat.com)
- docs: new section for admin parts of web UI (dcallagh@redhat.com)
- docs: admin guide for oVirt integration (dcallagh@redhat.com)
- make %%packages order predictable, fix tests (dcallagh@redhat.com)
- make autoincrement=True explicit for recipe_resource.id (dcallagh@redhat.com)

* Tue Nov 27 2012 Raymond Mancy <rmancy@redhat.com> 0.10.4-1
- 877029 Produce unique package list for a recipes package deps
  (rmancy@redhat.com)
- 879184 Fix for 'stealing' systems from currently running recipes
  (rmancy@redhat.com)

* Fri Nov 23 2012 Raymond Mancy <rmancy@redhat.com> 0.10.3-1
- 879146 Don't change existing FQDN in install_done (ncoghlan@redhat.com)

* Thu Nov 22 2012 Raymond Mancy <rmancy@redhat.com> 0.10.2-1
- Hotfix versions now bump the z in x.y.z

* Thu Nov 22 2012 Raymond Mancy <rmancy@redhat.com> 0.10.1-2
- 870908 add /tmp/packaging.log to anamon watch list (dcallagh@redhat.com)

* Mon Nov 19 2012 Raymond Mancy <rmancy@redhat.com> 0.10.1-1
- 863180 [RFE] add --lab-controller to beaker-import script (bpeck@redhat.com)
- 860870 Fix the navigation bar URLs for OS Version listing. (asaha@redhat.com)
- 866552 skip LDAP lookups for usernames containing '/' (dcallagh@redhat.com)
- 862061 power command fails if machine is in wrong state (bpeck@redhat.com)
- 864610 remove special handling of Decimal for rdflib (dcallagh@redhat.com)
- 655009 remove 'Virtual' system type (dcallagh@redhat.com)
- 655009 add install_done call to register hostname with Beaker
  (dcallagh@redhat.com)
- 816490 Support for search by min and max Job ID in the CLI (asaha@redhat.com)
- 840734 workflow-xslt: Fix jobxml_parsed variable declarations
  (davids@redhat.com)
- 867168 ensure provision commands aren't leaked in case of unhandled exception
  (dcallagh@redhat.com)
- 655009 allocate MAC addresses to guests (dcallagh@redhat.com)
- 598865 Expanded documentation for adding a task (rmancy@redhat.com)
- 728410 new snippet 'packages' to allow extra packages per system
  (dcallagh@redhat.com)
- 869455 only add Jobs to the session once they are fully populated
  (dcallagh@redhat.com)
- 584267 Update footer with version number and doc link (rmancy@redhat.com)
- 835367 run createrepo at task upload time, instead of recipe scheduling time
  (bpeck@redhat.com)
- 837709 DistroTree activity search page (rmancy@redhat.com)
- 607531 Link to a recipe's 'Possible Systems' (rmancy@redhat.com)
- 691442 Publish whiteboards for reserved systems (ncoghlan@redhat.com)
- 862970 Report "None" for unknown destructive and nda fields in task details
  (qwan@redhat.com)
- 865265 normalize log paths before inserting into the database
  (dcallagh@redhat.com)
- 862235 turn off Jinja caching for kickstart templates (dcallagh@redhat.com)
- 749512 Be explicit that tasks may not have their destructiveness defined.
  (ncoghlan@redhat.com)
- 695609 Initial glossary index (rmancy@redhat.com)
- 674025 Always show task specified by anchor. (asaha@redhat.com)
- 735054 Use 'curl' instead of 'wget' in RHEL 6+ and Fedora in Kickstarts.
  (asaha@redhat.com)
- 839116 Add Systems information in My Groups. (asaha@redhat.com)
- 860130 Wait for power state change when using ipmitool (ncoghlan@redhat.com)
- 862518 support for running recipes on RHEV/oVirt guests (dcallagh@redhat.com)
- 820793 unable to collect inventory from ppc64 system running RH6.3
  (bpeck@redhat.com)
- 626292 Improve description of recipeSet XML tag (ncoghlan@redhat.com)
- 740704 Updates to the Job RNG description. (asaha@redhat.com)
- 839116 Fix test case for systems view under My Groups (asaha@redhat.com)
- 740704 Update the priority values in the schema to match the actual allowed
  ones. (asaha@redhat.com)
- 691442 Fixes to whiteboard env var definitions (ncoghlan@redhat.com)
- 874675 update repo URL for Fedora ARM packages (dcallagh@redhat.com)
- 860870 Look for an element on the loaded page. (asaha@redhat.com)

- /distribution/inventory: acpidump and acpixtract are not needed
  (dcallagh@redhat.com)
- /distribution/inventory: add a parameter to show output instead of sending it
  (dcallagh@redhat.com)
- /distribution/inventory: capture output of pushInventory.py in case it fails
  (dcallagh@redhat.com)
- checkbugs.py: --release option to search by bug flags (dcallagh@redhat.com)
- simplify Recipe.roles and RecipeTask.roles (dcallagh@redhat.com)
- expose kickstart URL in job results XML (dcallagh@redhat.com)
- use postreboot instead of install_done for RHEV reboot hackery
  (dcallagh@redhat.com)
- use unpatched tarballs for tito build --test (dcallagh@redhat.com)
- allow sorting recipes grid by fqdn (dcallagh@redhat.com)

* Thu Oct 04 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.4-2
- fix DocBook syntax error (dcallagh@redhat.com)
- fix bash-completion problems in build (dcallagh@redhat.com)
- hide stderr from bkr in bash-completion script (dcallagh@redhat.com)
- Fixes for 853282 (rmancy@redhat.com)
- Fixes for 624393 (rmancy@redhat.com)
- fix tests (dcallagh@redhat.com)

* Fri Sep 28 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.4-1
- support for sending metrics to Graphite's carbon daemon (dcallagh@redhat.com)
- 847914 Fixed bug in distro_import.py relating to CenOS .treeinfo files
  (jdevries@redhat.com)
- 853497 use flock to prevent beaker_expire_distros cron jobs from running
  simultaneously (dcallagh@redhat.com)
- Added README file (rmancy@redhat.com)
- 842883 set -x in kickstart %%pre and %%post (dcallagh@redhat.com)
- 852902 don't let piwik.js hold up the document ready event
  (dcallagh@redhat.com)
- 854794 cleaned up log URL generation, fixed superfluous slashes
  (dcallagh@redhat.com)
- 768167 fix encoding issues with job XML (dcallagh@redhat.com)
- 853848 use requests to issue DELETE requests for log-delete
  (dcallagh@redhat.com)
- 853849 print failures in log-delete to stderr (dcallagh@redhat.com)
- 725661 remove whitespace in css. add exception handle for firefox console.
  fix a html error in template. (ryang@redhat.com)
- 852557 disable Visit and VisitIdentity table creation on startup
  (dcallagh@redhat.com)
- 855104 record deletion of install options in system history
  (dcallagh@redhat.com)
- 855974 ensure console logs are served as text/plain by Apache
  (dcallagh@redhat.com)
- 811241 custom 404 page for lab controller logs (dcallagh@redhat.com)
- 851176 Search job by retention tag and product. (rmancy@redhat.com)
- 526348 Test case for rhts-sync-block (bpeck@redhat.com)
- 853219 [RFE] please add ability to look up distro and distro_trees via id
  (bpeck@redhat.com)
- 857355 fix SystemStatusAttributeExtension for sqlalchemy 0.7
  (dcallagh@redhat.com)
- 856691 bash completion script for bkr (dcallagh@redhat.com)
- 857798 add signal handling in foreground mode. (asaha@redhat.com)
- moved beaker-wizard from rhts-devel (dcallagh@redhat.com)
- 822387 Implemented Jobs.filter() (jdevries@redhat.com)
- 856850 Use logging.shutdown to cleanup (asaha@redhat.com)
- __requires__ for CherryPy 2 compat package on Fedora (dcallagh@redhat.com)
- sqlalchemy 0.7 no longer accepts a list in .join()/.outerjoin()
  (dcallagh@redhat.com)
- fix Requires for Fedora (dcallagh@redhat.com)
- 859400 delay for 5 seconds between 'off' and 'on' when rebooting
  (dcallagh@redhat.com)
- 857342 added man page for beaker-wizard (dcallagh@redhat.com)
- 858122 Fixes job matrix functionality with sqlalchemy 0.7 (asaha@redhat.com)
- 624393 Added xml and prettyxml option to `bkr task-details`
  (rmancy@redhat.com)
- 605561 anamon: avoid race in reading /proc/mounts during shutdown
  (dcallagh@redhat.com)
- new block-level statement {%% snippet %%} equivalent to {{ snippet() }}
  (dcallagh@redhat.com)
- 801676 move ssh_keys snippet to inside rhts_post (dcallagh@redhat.com)
- 842907 Some improvements to the msg bus code. (rmancy@redhat.com)
- 790312 Documented the '<hypervisor/>' element (rmancy@redhat.com)
- 633369 RFE: custom repos available at install time. (bpeck@redhat.com)
- 717424 Expire by distro (rmancy@redhat.com)
- 854364 Update hostRequires to search parity with the web UI
  (bpeck@redhat.com)
- 833275 Fix for Duplicate Ids in Excluded Families Tab (asaha@redhat.com)
- 854434 allow looking up logs by any job component, not just recipe
  (dcallagh@redhat.com)
- 853282 --limit option for log-delete (rmancy@redhat.com)

* Sat Sep 08 2012 Bill Peck <bpeck@redhat.com> 0.9.3-7
- Hotfix for beaker-transfer, if a recipe has no logs it will cause a
  traceback. (bpeck@redhat.com)

* Tue Sep 04 2012 Bill Peck <bpeck@redhat.com> 0.9.3-6
- Fix pxe conflicts between arm and x86 systems. (bpeck@redhat.com)

* Thu Aug 30 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.3-5
- Merge hotfix from 0.9.2 (dcallagh@redhat.com)

* Wed Aug 29 2012 Bill Peck <bpeck@redhat.com> 0.9.2-3
- Fix for log-delete to send trailing slashes. (bpeck@redhat.com)

* Wed Aug 29 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.3-4
- Update to arm support. (bpeck@redhat.com)

* Tue Aug 28 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.3-3
- fix whitespace for highbank and mvebu snippets (dcallagh@redhat.com)
- Fix SchemaUpgrade docs, we were missing the updates to image_type ENUM
  (bpeck@redhat.com)

* Fri Aug 24 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.3-2
- fix server API docs build (dcallagh@redhat.com)

* Fri Aug 24 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.3-1
- Add missing tr and tbody elements to my_paginate_datagrid (stl@redhat.com)
- remove dead koan-related bits (dcallagh@redhat.com)
- tests: fix race in test_max_whiteboard (dcallagh@redhat.com)
- 806113 rhts_partitions: /boot needs --asprimary, but / and swap do not
  (dcallagh@redhat.com)
- 743441 new ks_meta variable 'rootfstype' to customise the root filesystem
  type (dcallagh@redhat.com)
- 847629 fix DistroTree.url_in_lab when an unusual URL scheme is present
  (dcallagh@redhat.com)
- 582008 allow users to see secret systems when loaned to them
  (dcallagh@redhat.com)
- 831448 support op="!=" in <distrolabcontroller/> and <hostlabcontroller/>
  (dcallagh@redhat.com)
- 841197 Beaker ignores tasks, no error reported (bpeck@redhat.com)
- 623933 if RESERVE_IF_FAIL=1 is passed to task then it will only reserve on
  failure (bpeck@redhat.com)
- 849818 handle NULL recipetask_id in watchdogs grid (dcallagh@redhat.com)
- 578812 new ks_meta variable static_networks (dcallagh@redhat.com)
- 841969 [RFE] Add arm support to beaker-provision (bpeck@redhat.com)
- 843854 %%post power commands need to be synchronous (bpeck@redhat.com)
- 630902 allow filtering distros by lab controller in reserve workflow
  (dcallagh@redhat.com)
- 838615 Custom kickstart documented (rmancy@redhat.com)
- 844517 Fix searchbar js error (rmancy@redhat.com)

* Wed Aug 08 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.2-2
- Abort beaker-init if no admin account exists or is specified (stl@redhat.com)
- Display condition report in system view similarly to system edit
  (rmancy@redhat.com)

* Fri Aug 03 2012 Bill Peck <bpeck@redhat.com> 0.9.2-1
- 830288 RFE: Please extend the watchdog panic time to 10 minutes
  (bpeck@redhat.com)
- Bump test time on beaker/import task (bpeck@redhat.com)
- do not run jobs on beaker import task. (bpeck@redhat.com)
- 572834 new 'interrupt' power command, for sending an NMI or break to the
  system (dcallagh@redhat.com)
- 840983 [RFE] add ignoredisk to ks_meta support, also fix up the docs to
  match. (bpeck@redhat.com)
- 841743 [RFE] bkr command option to turn off panic detection for submitting
  task (bpeck@redhat.com)
- tests: fix kickstart tests when mounted at /bkr/ (dcallagh@redhat.com)
- 841619 Allow importing without a .composeinfo and .treeinfo.
  (bpeck@redhat.com)
- 572834 proxy method for triggering a power command (dcallagh@redhat.com)
- 841398 special case lazy_create for DeviceClass to handle None -> "NONE"
  (dcallagh@redhat.com)
- 838671 Set a default root password for new installations (stl@redhat.com)
- 841105 Remove spurious html elements (rmancy@redhat.com)
- 841749 [RFE] server config parameter to set external URL (bpeck@redhat.com)
- 843561 PPC64 installs fail after 0.9 upgrade (bpeck@redhat.com)
- tests: fixes for distro and distro tree search (dcallagh@redhat.com)
- 844512 return false from onclick handlers in search bar (dcallagh@redhat.com)
- 805019 Support GET URL for displaying executed tasks by recipe task id
  (rmancy@redhat.com)
- 840084 Document REBOOTCOUNT (rmancy@redhat.com)
- 839820 expose distro XML filter for XML-RPC, bkr client, and beaker-pxemenu
  (dcallagh@redhat.com)
- 690063 allow searching for key with any value in hostRequires XML
  (dcallagh@redhat.com)
- 690063 expose systems XML filter for bkr list-systems (dcallagh@redhat.com)
- update beaker-repo-update's default URL to beaker-project.org
  (dcallagh@redhat.com)
- 835355 Make system groups work on '/bkr' mounted installations
  (rmancy@redhat.com)
- 842923 Reduce data set loaded by log_delete. (rmancy@redhat.com)
- 840720 filter and sort "Family" dropdown in task search form
  (dcallagh@redhat.com)
- 839093 Do not convert CSV-exported False bools to empty strings
  (stl@redhat.com)
- 790484 Seperate system page into view and edit mode (rmancy@redhat.com)
- 835179 Fix task search from giving memory error (rmancy@redhat.com)
- 817518 console.log for host should be updated until whole recipeset completes
  (bpeck@redhat.com)
- add back trailing slash to harness URL (dcallagh@redhat.com)
- Fix doubling of url() on form action (rmancy@redhat.com)
- 841975 [RFE] support url method for deleteing a systems pxe record
  (bpeck@redhat.com)

* Thu Jul 19 2012 Raymond Mancy <rmancy@redhat.com> 0.9.1-3
- Ensure job actions are not on newlines regardless of whiteboard length. See
  732025 (rmancy@redhat.com)

* Wed Jul 18 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.1-2
- Improvement on error msg for invalid product/tag combos. See bug 821287
  (rmancy@redhat.com)
- group_permission.js was still using the old do_and_confirm
  (rmancy@redhat.com)
- Add confirmation for groups remove. Also removed 'Remove' from regular groups
  page. See bug 743025 (rmancy@redhat.com)
- 840724 Add NOT NULL property to group_activity.group_id and add SQL
  statements to accomodate (rmancy@redhat.com)
- Fix for some weird formatting on job page introduced by 732025
  (rmancy@redhat.com)
- This fixes hover highlighting on the system page; introduced by 732024.
  (rmancy@redhat.com)

* Fri Jul 13 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.1-1
- typo _all_ should be __all__ (rmancy@redhat.com)
- 782284 expand CPU flag column (dcallagh@redhat.com)
- 822492 allow whiteboard to wrap on job and recipe pages (dcallagh@redhat.com)
- 802842 strict CSV parsing for imports (dcallagh@redhat.com)
- Update import to run jobs (bpeck@redhat.com)
- 732024 Coloured indicators for status and result text for the jobs and
  recipes page. (rmancy@redhat.com)
- 823400 Start RepeatTimer for message bus auth (rmancy@redhat.com)
- 732025 Job actions are now on a single line with added padding between them
  (rmancy@redhat.com)
- fix typo in CSV import (dcallagh@redhat.com)
- 820724 [RFE] beaker-import should support --family (bpeck@redhat.com)
- 836396 add exponential backoff for power command retries
  (dcallagh@redhat.com)
- 835753 update bkr system-provision options to reflect the new Cobbler-less
  reality (dcallagh@redhat.com)
- 836603 Fix typo, DistoTree to DistroTree (rmancy@redhat.com)
- 830475 strip and validate SSH keys; write them out safely
  (dcallagh@redhat.com)
- 837710 ignore failures when reprovisioning a system on release
  (dcallagh@redhat.com)
- 595512 show friendly error for invalid taskspec arguments
  (dcallagh@redhat.com)
- 811404 generate yum config file for repos in a distro tree
  (dcallagh@redhat.com)
- 837460 serialize power commands by power address (dcallagh@redhat.com)
- increase verbosity of power scripts where possible (dcallagh@redhat.com)
- ping power controller before running ipmilan (dcallagh@redhat.com)
- 835912 Speed up of /recipes page (rmancy@redhat.com)
- 646773 pass Beaker server URL to test machines as $BEAKER
  (dcallagh@redhat.com)
- 749698 show a warning with link to reservation policy, if configured
  (dcallagh@redhat.com)
- 838571 Remove rhel7/ppc64 boot order workaround, add leavebootorder to
  bootargs (bpeck@redhat.com)
- 799029 [RFE] Make console.log even more readable remove whole ansi sequences
  (bpeck@redhat.com)
- 732026 Progressbar redesigned (mganisin@redhat.com)
- 825774 Fix for report problem with multiple recipes on a job page
  (rmancy@redhat.com)
- 649608 bkr job-cancel can cancel other people's job (bpeck@redhat.com)
- 835594 lab controller can't lookup secret/NDA machines (bpeck@redhat.com)
- 821287 Added ability to modify Job retention tag and product via bkr client
  (rmancy@redhat.com)
- 835373 re-introduce clear_logs command for clearing console logs
  (dcallagh@redhat.com)
- 767243 Added more search options for distro and distrotrees.
  (rmancy@redhat.com)
- 834147 support distros imported as ftp:// but not http://
  (dcallagh@redhat.com)
- 670868 allow marshalling None in beaker-proxy (dcallagh@redhat.com)
- 743025 Ask users for confirmation before deleting DB entities.
  (rmancy@redhat.com)
- 747000 Create Activity page for Lab Controller (rmancy@redhat.com)
- 817525 Fixes problem with toggling some columns on reserve system page
  (rmancy@redhat.com)

* Mon Jul 02 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-7
- 836325 [BUG] don't try and modify /etc/sysconfig/ntpd if it doesn't exist.
  (bpeck@redhat.com)
- 836637 [BUG] skipx doesn't work as expected in the kickstarts
  (bpeck@redhat.com)

* Fri Jun 29 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-6
- fix build for RHEL5 and F16 (dcallagh@redhat.com)

* Fri Jun 29 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-5
- 835319 fix typo in bkr distro-trees-list (dcallagh@redhat.com)
- RHEL7 build fixes (dcallagh@redhat.com)

* Tue Jun 26 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-4
- bkr client: sys was not imported and was causing an error (rmancy@redhat.com)
- fix watchdog death if console log does not exist (dcallagh@redhat.com)

* Thu Jun 21 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-3
- 833582 [BUG] missing apc_snmp_then_etherwake power command (bpeck@redhat.com)
- 832975 S390 kickstarts should have reboot command (RHEL7) (bpeck@redhat.com)
- 832226 Reboot snippets must be the last thing in a kickstart (stl@redhat.com)
- 833662 atomically replace link targets in netboot image cache code
  (dcallagh@redhat.com)
- delay for 30 seconds before rebooting in postreboot snippet
  (dcallagh@redhat.com)
- 828927 API for getting the last installed distro tree for a system
  (dcallagh@redhat.com)
- Revert "clear console logs when provisioning" (dcallagh@redhat.com)
- 821948 clear console log when watchdog is removed (dcallagh@redhat.com)
- 833842 [BUG] Manual provisioning fails on most families/arches
  (bpeck@redhat.com)

* Mon Jun 18 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-2
- 828451 Update lpar command to include the hmc. (bpeck@redhat.com)
- 823329 avoid processing the same recipe many times in queued_recipes
  (dcallagh@redhat.com)
- Fix for job-modify --response for ack/nak'ing already ack/nak'ed jobs
  (rmancy@redhat.com)
- 829984 replace yaboot symlink if it already exists, instead of dying
  (dcallagh@redhat.com)
- 829423 no more distro_tree tag means we need to change how we tag STABLE
  (bpeck@redhat.com)
- 830937 [BUG] beaker-import imports RHEL5 ppc64 as ppc. (bpeck@redhat.com)
- 830945 [BUG] beaker-import should fall back to .discinfo if timestamp is not
  defined in .treeinfo. (bpeck@redhat.com)
- 831864 can't join on Group.systems (dcallagh@redhat.com)
- 830940 don't offer to provision distro-trees which have been expired
  (dcallagh@redhat.com)
- A few more enhancements for 812831 (rmancy@redhat.com)
- 832250 fix race between spawning and reaping MonitoredSubprocesses
  (dcallagh@redhat.com)
- 832328 use an event instead of an exception to trigger shutdown in beaker-
  provision (dcallagh@redhat.com)
- 829981 nvram command doesn't exist in all distros (dcallagh@redhat.com)
- custom tito builder which generates nice patches for hotfix releases
  (dcallagh@redhat.com)
- fix some warnings/mistakes in sphinx docs (dcallagh@redhat.com)
- adjust client man page titles (dcallagh@redhat.com)
- sqlalchemy.exceptions has been removed in SQLAlchemy 0.7
  (dcallagh@redhat.com)

* Thu Jun 07 2012 Bill Peck <bpeck@redhat.com> 0.8.2-12
- HOTFIX - don't try and process non nfs url's as nfs. (bpeck@redhat.com)

* Wed Jun 06 2012 Bill Peck <bpeck@redhat.com> 0.8.2-11
- Add RHS import support into beaker-import (bpeck@redhat.com)
- 828947 add ability to provide options to nfs installs, also --ks-meta for
  workflows (bpeck@redhat.com)
- 822426 Fixing up some problems that Key/Value search encountered after sqla
  upgrade. (rmancy@redhat.com)

* Fri Jun 01 2012 Dan Callaghan <dcallagh@redhat.com> 0.9.0-1
- Cobbler removal, a.k.a. "native provisioning"
- 815325 Needed to update the prefs form to handle correct email validation
  (rmancy@redhat.com)
- 817122 Fails to upload device data (bpeck@redhat.com)
- 809076 Searching by owner in job page now searches by user name, not email.
  New option for searching by email (rmancy@redhat.com)
- 732021 'My Jobs' link on front page (rmancy@redhat.com)
- 813118 Activity tweaks (rmancy@redhat.com)
- 820111 Fix Pagination and row count issues by ensuring duplicate rows are not
  returned in system search (rmancy@redhat.com)
- 772904 Execute older tasks first (bpeck@redhat.com)
- 750406 User groups listing (rmancy@redhat.com)
- 760691 RFE: Add netboot method detection to kickstart post and inventory
  scripts (bpeck@redhat.com)
- 812831 Ack/Nak a job or recipe set from the cmd line (rmancy@redhat.com)
- 817568 Fix join to not give error on groups' system page.
  (rmancy@localhost.localdomain)
- 602741 Expand system searching to include Devices/Subsys_device_id and
  Devices/Subsys_vendor_id (rmancy@redhat.com)
- 820719 add support for RHS2 (bpeck@redhat.com)
- 820328 RHEL7 ppc changes boot order (bpeck@redhat.com)
- 818628 add %%end to RHEL7 post_s390_reboot snippet (bpeck@redhat.com)
- fix -c option to beaker-proxy (dcallagh@redhat.com)
- 821602 Improved bkr distros-list display (dcallagh@redhat.com)
- 809704 send Anaconda scriptlet output to /dev/console in custom kickstarts
  (dcallagh@redhat.com)
- 824050 don't create empty WHERE clauses (dcallagh@redhat.com)
- 822426 Fixing up some problems that Key/Value search encountered after sqla
  upgrade. (rmancy@redhat.com)
- 817120 add pci-device and arch searching to list-systems command
  (bpeck@redhat.com)
- add RHS support to beaker-import (bpeck@redhat.com)
- beaker-import: fall back to Last-Modified header if tree has no timestamp
  (dcallagh@redhat.com)

* Mon May 28 2012 Dan Callaghan <dcallagh@redhat.com> 0.8.2-10
- Rhel7 set end=%%end for custom kickstarts (bpeck@redhat.com)
- Backport rhel7/ppc boot order (bpeck@redhat.com)

* Wed May 23 2012 Bill Peck <bpeck@redhat.com> 0.8.2-9
- fix beakertito tagging (bpeck@redhat.com)
- [BUG] If a tree didn't have any addon repos it wouldn't get the composeinfo
  repos either (bpeck@redhat.com)

* Tue May 22 2012 Bill Peck <bpeck@redhat.com> 0.8.2-8
- HOTFIX - update distro_import to handle .composeinfo changes.
  (bpeck@redhat.com)

* Fri Apr 27 2012 Bill Peck <bpeck@redhat.com> 0.8.2-7
- 816879 Missing task metadata: Types, RunFor, Requires (bpeck@redhat.com)

* Fri Apr 27 2012 Dan Callaghan <dcallagh@redhat.com> 0.8.2-6
- 816553 add missing unique constraints (dcallagh@redhat.com)

* Thu Apr 19 2012 Raymond Mancy <rmancy@redhat.com> 0.8.2-5
- Change Group's permissions table header to 'Permissions', and moved 'Contact
  Owner' link to be beside owner field. (rmancy@redhat.com)
- fix register and upload file methods to use lazy_create (bpeck@redhat.com)
- 585153 report an error if T: or TR: is passed to bkr job-logs
  (dcallagh@redhat.com)
* Wed Apr 18 2012 Raymond Mancy <rmancy@redhat.com> 0.8.2-4
- 813642 Check each named beakerd thread instead of relying on active thread count
  (stl@redhat.com)
- 731615 fix <device/> to not add an empty query. (bpeck@redhat.com)

* Tue Apr 17 2012 Raymond Mancy <rmancy@redhat.com> 0.8.2-3
- test: Fix job.id to be id of recipe (rmancy@redhat.com)
- 731615 fix mistake in RELAX NG schema for <device/> (dcallagh@redhat.com)
- 812722 Remove pidfile if it exists before starting beakerd (stl@redhat.com)
* Fri Apr 13 2012 Raymond Mancy <rmancy@redhat.com> 0.8.2-2
- more %%d issues in command_queue. (bpeck@redhat.com)
- Merge remote branch 'origin/release-0.8.1-5.1' into release-0.8.2
  (rmancy@redhat.com)
* Fri Apr 13 2012 Steven Lawrance <stl@redhat.com> 0.8.1-5.2
- more %%d issues in command_queue. (bpeck@redhat.com)

* Thu Apr 12 2012 Raymond Mancy <rmancy@redhat.com> 0.8.2-1
- 740321 Do not show power control buttons when system has no lab controller
  (stl@redhat.com)
- 745254 Store the default root password in the database (stl@redhat.com)
- 743663 Reject job submission if user's root password has expired
  (stl@redhat.com)
- 782075 Permit whitespace in ssh public key descriptions (stl@redhat.com)
- 784875 add support for RedHatStorageSoftwareAppliance3 (bpeck@redhat.com)
- 743819 add bkr watchdogs-extend command. (bpeck@redhat.com)
- 773702 dead recipes routine processes the same recipe mutliple times
  (bpeck@redhat.com)
- 572836 Collect crash dump information useful for analysis when test
  panics/stalls (bpeck@redhat.com)
- 742569 delete system should be available over command line.
  (bpeck@redhat.com)
- 794543 also look for 'pxe' in EFI boot options (dcallagh@redhat.com)
- 740957 only show systems of type Machine in reserve workflow
  (dcallagh@redhat.com)
- 797584 merge system_admin_map table into system_group (dcallagh@redhat.com)
- 773124 use a nested transaction to avoid races in MappedObject.lazy_create
  (dcallagh@redhat.com)
- 585153 new bkr job-logs command to print URLs of recipe logs
  (dcallagh@redhat.com)
- 784237 prevent and handle invalid addresses in <cc/> (dcallagh@redhat.com)
- 731615 support for selecting systems by device in recipes
  (dcallagh@redhat.com)
- 797162 Only update /etc/sysconfig/nptd with '-x' if it does not contain '-g'
  (rmancy@redhat.com)
- 750623 Ability to add permissions to group via the Groups page.
  (rmancy@redhat.com)
- 746093 Create ajax widgets for users wanting to report system problems and
  request loans (rmancy@redhat.com)
- 743319 add 'ignoredisk --interactive' if people select manual in ks_meta.
  (ryang@redhat.com)
- 751949 Remove log entries for already deleted jobs (rmancy@redhat.com)
- 781369 Fix error when using '--wait' option on beaker client commands.
  (rmancy@redhat.com)
- 784863 Fix 500 when entering duplicate emails (rmancy@redhat.com)
- 785048 Replace None with an empty string in csv export. (rmancy@redhat.com)
- 772882 Clean duplicate required package list when uploading new tasks.
  (ryang@redhat.com)
- 747974 Only clear specially partitions if ondisk option is given. 
  (ryang@redhat.com)

- /distribution/beaker/custom_kickstart: initial version of test
  (dcallagh@redhat.com)
- tests: disable "slowness" test for large results (dcallagh@redhat.com)
- Remove bkr.inttest.server.test_max_whiteboard, not relevant.
  (rmancy@redhat.com)
- avoid multiple concurrent get_distros AJAX requests (dcallagh@redhat.com)
- avoid extraneous joins and DISTINCT on system grid pages
  (dcallagh@redhat.com)
- more resilient logging in command queue thread (dcallagh@redhat.com)
- Use python-daemon in beakerd (stl@redhat.com)
- qpid: Remove use of headers exchange, add direct (rmancy@redhat.com)
- New option --suppress-install-task (mganisin@redhat.com)

* Tue Apr 10 2012 Bill Peck <bpeck@redhat.com> 0.8.1-5.1
- more resilient logging in command queue thread (dcallagh@redhat.com)

* Wed Apr 04 2012 Raymond Mancy <rmancy@redhat.com> 0.8.1-9
- service queue msgs' fixed to also be sent on direct exchange
  (rmancy@redhat.com)

* Tue Apr 03 2012 Raymond Mancy <rmancy@redhat.com> 0.8.1-8
- Put service queue messages onto direct exchange, not just default exchange
  (rmancy@redhat.com)

* Tue Apr 03 2012 Raymond Mancy <rmancy@redhat.com> 0.8.1-7
- Fix _auth_interval typo, and change eso.topic subjects to be prefixed with
  beaker.* (rmancy@redhat.com)

* Wed Mar 21 2012 Raymond Mancy <rmancy@redhat.com> 0.8.1-6
- Qpid changes (rmancy@redhat.com)

* Fri Mar 16 2012 Bill Peck <bpeck@redhat.com> 0.8.1-5
- 803713 Fix for job matrix result box not generating links with 'job_ids' when
  being generated via job id box (rmancy@redhat.com)
- More s390 fixes. (bpeck@redhat.com)
- beaker-import will fail if no repos are found in .treeinfo.
  (bpeck@redhat.com)
- 804162 job matrix ignores hide naks (bpeck@redhat.com)

* Thu Mar 08 2012 Raymond Mancy <rmancy@redhat.com> 0.8.1-4
- 790293 Fix for Login thread dying on lab controller (rmancy@redhat.com)

* Mon Feb 27 2012 Bill Peck <bpeck@redhat.com> 0.8.1-3
- 796621 "Kernel Options" not populated correctly if "=" character is included
  inside parameter (bpeck@redhat.com)
- 796647 move print_repos to rhts_post so that custom kickstarts pick this up.
  (bpeck@redhat.com)
- fix beaker-import to not crash when --root isn't used. (bpeck@redhat.com)

* Mon Feb 27 2012 Bill Peck <bpeck@redhat.com> 0.8.0-29
- fix beaker-import to not crash when --root isn't used. (bpeck@redhat.com)

* Thu Feb 23 2012 Bill Peck <bpeck@redhat.com> 0.8.0-28
- 796621 "Kernel Options" not populated correctly if "=" character is included
  inside parameter (bpeck@redhat.com)
- 796647 move print_repos to rhts_post so that custom kickstarts pick this up.
  (bpeck@redhat.com)

* Thu Feb 23 2012 Dan Callaghan <dcallagh@redhat.com> 0.8.1-2
- Merge hotfixes from release-0.8.0 branch

* Thu Feb 23 2012 Dan Callaghan <dcallagh@redhat.com> 0.8.0-27
- Merge "replacement for the real do_POST, to work around RHBZ#789790" for real
  this time (dcallagh@redhat.com)

* Thu Feb 23 2012 Steven Lawrance <stl@redhat.com> 0.8.0-26
- 796420 beaker-import should not abort on missing .treeinfo. print warning and
  continue (bpeck@redhat.com)
- 796403 Add an end tag to SSH keys ks_appends for RHEL7 (stl@redhat.com)

* Fri Feb 17 2012 Bill Peck <bpeck@redhat.com> 0.8.0-25.1
- bump release after pulling in do_POST commit 

* Fri Feb 17 2012 Bill Peck <bpeck@redhat.com> 0.8.0-25
- Support for RHEL7 (bpeck@redhat.com)

* Fri Feb 17 2012 Bill Peck <bpeck@redhat.com> 0.8.0-24.1
- replacement for the real do_POST, to work around RHBZ#789790.
  (bpeck@redhat.com)

* Tue Feb 07 2012 Bill Peck <bpeck@redhat.com> 0.8.0-24
- 786352 Limit number of concurrent power commands (stl@redhat.com)
- avoid creating subprofiles in Cobbler (dcallagh@redhat.com)

* Tue Jan 24 2012 Dan Callaghan <dcallagh@redhat.com> 0.8.1-1
- 541295 Ability to delete system notes (rmancy@redhat.com)
- 741860 Fix system search over multiple Key/Value search values
  (rmancy@redhat.com)
- 747328 Stop people from taking machines by surreptitious means
  (rmancy@redhat.com)
- 747767 fix 'None' values and missing rows in CSV install options export
  (dcallagh@redhat.com)
- 749441 set MySQL connection character set to utf8 (dcallagh@redhat.com)
- 749441 limit MAC address field to 18 chars (dcallagh@redhat.com)
- 736199 use testinfo.py from rhts (dcallagh@redhat.com)
- 735913 use .textContent instead of $().text() in local_datetime.js
  (dcallagh@redhat.com)
- 743065 Reserve workflow now only shows distros that are attached to lab
  controllers (rmancy@redhat.com)
- 747086 Fixed 500 ISE when renaming systems not attached to an LC
  (rmancy@redhat.com)
- 751330 use joinedloads to avoid N^4 queries when rendering job results
  (dcallagh@redhat.com)
- 754872 beaker-repo-update: use repo url as repo id (dcallagh@redhat.com)
- test for bug 741170: cannot submit jobs with xmlns (dcallagh@redhat.com)
- 541280 Add password field to user profile for root password on provisioned
  system (stl@redhat.com)
- 743666 Add a callback to power commands (stl@redhat.com)
- 743665 Check the strength of a user's root password if possible
  (stl@redhat.com)
- 645635 test that CSV export obeys system privacy (dcallagh@redhat.com)
- 770109 fix typo in search bar template ('operations' -> 'operation')
  (dcallagh@redhat.com)
- 747614 Remove and disable readahead collector (mcsontos@redhat.com)
- 765717 RFE make yum quiet when it pulls repos in %%post for the first time
  (bpeck@redhat.com)
- 772538 Do not immediately abort power commands if communication with Cobbler
  fails (stl@redhat.com)
- 773049 Don't allow job matrix to show deleted jobs (rmancy@redhat.com)
- 781568 Remove distro mapping when a lab controller is removed
  (stl@redhat.com)
- 769286 Fix distro search page to show correct count with sqla 0.6.8
  (rmancy@redhat.com)
- 771215 Matrix whiteboard now correctly shows tasks when clicking on results
  (rmancy@redhat.com)
- 771993 Fix the way that systemgroup admins are handled to work with sqla 0.6
  (rmancy@redhat.com)
- use ORM features for broken system detection (dcallagh@redhat.com)
- reduce recipe.log_server to VARCHAR(255) (dcallagh@redhat.com)
- fix use of tmpnam in unit tests (dcallagh@redhat.com)
- clean up shipped logging configuration (dcallagh@redhat.com)
- if HARNESSREPO is passed then pull in a newer harness (bpeck@redhat.com)
- clean up lab controller logging (dcallagh@redhat.com)
- integration tests now require python-requests (dcallagh@redhat.com)
- clean up and simplify query on watchdogs page (dcallagh@redhat.com)
- Consolidate the two inventory scripts (stl@redhat.com)
- TaskStatus.max can benefit from caching (dcallagh@redhat.com)
- add index to job.deleted and job.to_delete columns (dcallagh@redhat.com)

* Wed Dec 21 2011 Bill Peck <bpeck@redhat.com> 0.8.0-23
- anaconda doesn't handle nfs:// repos that are relative. (bpeck@redhat.com)

* Tue Dec 20 2011 Bill Peck <bpeck@redhat.com> 0.8.0-22
- update find_kickstart to ignore sample_end.ks as well. (bpeck@redhat.com)

* Mon Dec 19 2011 Bill Peck <bpeck@redhat.com> 0.8.0-21
- fix for beaker-transfer (bpeck@redhat.com)

* Thu Dec 15 2011 Bill Peck <bpeck@redhat.com> 0.8.0-20
- cast osminor to a char so when we do the db compare its done correctly.
  (bpeck@redhat.com)

* Tue Dec 13 2011 Bill Peck <bpeck@redhat.com> 0.8.0-19
- duplicate short options (bpeck@redhat.com)

* Tue Dec 13 2011 Bill Peck <bpeck@redhat.com> 0.8.0-18
- add options to beaker-osversion (bpeck@redhat.com)

* Thu Dec 01 2011 Bill Peck <bpeck@redhat.com> 0.8.0-17
- Failed to query rcm for repos (bpeck@redhat.com)

* Tue Nov 22 2011 Bill Peck <bpeck@redhat.com> 0.8.0-16
- Revert "avoid races in MappedObject.lazy_create" (dcallagh@redhat.com)
- 752869 work around race condition in Distro.lazy_create (dcallagh@redhat.com)

* Thu Nov 17 2011 Dan Callaghan <dcallagh@redhat.com> 0.8.0-15
- 754553 beaker-repo-update creates repos that won't work on rhel5
  (bpeck@redhat.com)
- 746752 beaker-transfer ignores os.link errors (bpeck@redhat.com)
- 746752 add logging to upload.py (bpeck@redhat.com)
- 752869 avoid races in MappedObject.lazy_create (dcallagh@redhat.com)

* Tue Nov 15 2011 Bill Peck <bpeck@redhat.com> 0.8.0-14
- rename rhts_lab_import to beaker_lab_import (bpeck@redhat.com)

* Tue Nov 15 2011 Bill Peck <bpeck@redhat.com> 0.8.0-13
- 754133 RHEL5 kickstarts don't support --cost option to repo command
  (bpeck@redhat.com)

* Tue Nov 15 2011 Bill Peck <bpeck@redhat.com> 0.8.0-12
- 753976 beakerd cannot abort recipes: RequestRequiredException
  (bpeck@redhat.com)

* Tue Nov 15 2011 Dan Callaghan <dcallagh@redhat.com> 0.8.0-11
- Revert fix for bug 752869: "race condition when adding distros"
  (dcallagh@redhat.com)

* Fri Nov 11 2011 Dan Callaghan <dcallagh@redhat.com> 0.8.0-10
- 752869 race condition when adding distros (bpeck@redhat.com)
- clean up lab controller logging (dcallagh@redhat.com)
- timed handling of session renewal for qpid (rmancy@redhat.com)
- 749551 try except handling in wrong place for beaker-watchdog
  (bpeck@redhat.com)

* Tue Nov 08 2011 Bill Peck <bpeck@redhat.com> 0.8.0-9
- add --quiet option to bkr workflows to not print ignored tasks
  (bpeck@redhat.com)
- 751868 osversion.trigger can fail to add a new distro (bpeck@redhat.com)
- Don't iterate ignored profiles. (bpeck@redhat.com)

* Mon Nov 07 2011 Dan Callaghan <dcallagh@redhat.com> 0.8.0-8
- 746774 correctly handle multiple status changes within the same second
  (dcallagh@redhat.com)

* Thu Nov 03 2011 Bill Peck <bpeck@redhat.com> 0.8.0-7
- 750428 workaround to force TGMochiKit to be always initialised
  (dcallagh@redhat.com)
- beaker-osversion will die on inherited profiles (bpeck@redhat.com)

* Wed Nov 02 2011 Raymond Mancy <rmancy@redhat.com> 0.8.0-6
- fixes for integration tests

* Fri Oct 28 2011 Bill Peck <bpeck@redhat.com> 0.8.0-5
- fix warnings from osversion.trigger and remove osversion_data after
  10 days

* Fri Oct 28 2011 Bill Peck <bpeck@redhat.com> 0.8.0-4
- 749242 removed log-delete deprecation error

* Thu Oct 27 2011 Bill Peck <bpeck@redhat.com> 0.8.0-3
- add missing continue statements

* Wed Oct 26 2011 Bill Peck <bpeck@redhat.com> 0.8.0-2
- 718119 new osversion.trigger
- 746683 bkr whoami command added

* Tue Oct 18 2011 Dan Callaghan <dcallagh@redhat.com> 0.7.3-6
- 746774 correctly handle multiple status changes within the same second
  (dcallagh@redhat.com)

* Mon Oct 10 2011 Dan Callaghan <dcallagh@redhat.com> 0.8.0-1
- upgrade to sqlalchemy 0.6, TurboGears 1.1, Python 2.6 for server and lab
  controller (dcallagh@redhat.com)
- 743852 Filter buttons in Recipe view not working (Queued, Running recipes)
  (bpeck@redhat.com)

* Fri Oct 07 2011 Raymond Mancy <rmancy@redhat.com> 0.7.3-5
- Altered upgrade_0.7.2.txt notes to not include the 0.7.2 schema
  changes other than the rollback, which is pointed to by the
  upgrade_0.7.03.txt (rmancy@redhat.com)

* Wed Oct 05 2011 Raymond Mancy <rmancy@redhat.com> 0.7.3-4
- Merge the two upgrade notes for 0.7.03 (rmancy@redhat.com)
- unreserve() will now catch all exceptions, including if cobbler is
  down (rmancy@redhat.com)

* Mon Oct 03 2011 Raymond Mancy <rmancy@redhat.com> 0.7.3-2
- Fix for ks_appends broken by ssh keys patch (stl@redhat.com)
- temporary hack for building in dist-f14 (dcallagh@redhat.com)

* Fri Sep 30 2011 Raymond Mancy <rmancy@redhat.com> 0.7.3-1
- 739893 - Client option to print xml of existing job
  (j-nomura@ce.jp.nec.com)
- 729654 - Requires from Makefile are not installed during kickstart
  (bpeck@redhat.com)
- 725537 - Add configurability to the lab controller's rotating file logger.
  (rmancy@redhat.com)
- 737933 - Make bkr task-details only list valid == True task as default
  (ryang@redhat.com)
- 738006 - recipe.kickPart documented but not implemented? (bpeck@redhat.com)
- 676713 - Page scrolling links at bottom of page (atodorov@redhat.com)
- 742115 - fix sphinx autodoc failure, and catch any future ones
  (dcallagh@redhat.com)
- 734535 - drop server from each log entry and store log_server in recipe.
  (bpeck@redhat.com)
- 693403 - [RFE] add way how to specify hostRequires in `bkr workflow-simple`
  (bpeck@redhat.com)
- 738423 - abort and cancel should ignore release_action failures
  (bpeck@redhat.com)
- 630863 - Show link to current running job in system form
  (rmancy@redhat.com)

- Turn soft limits into hard ones (mcsontos@redhat.com)
- test for qpid bug https://bugzilla.redhat.com/show_bug.cgi?id=733543
  (rmancy@redhat.com)

* Wed Sep 21 2011 Raymond Mancy <rmancy@redhat.com> 0.7.2-3
- Moved content from bz734535.sql into update_0.7.2.txt and added
  rollback SQL

* Mon Sep 19 2011 Raymond Mancy <rmancy@redhat.com> 0.7.2-2
- Fix for bug introduced by 713578 that caused the submission kw args
  from the job page to change. (rmancy@redhat.com)
- 739178 remove_distro can throw an exception if the distro doesn't
  exist in beaker (bpeck@redhat.com)
- 734535 urlparse already imported (bpeck@redhat.com)

* Fri Sep 16 2011 Raymond Mancy <rmancy@redhat.com> 0.7.2-1
- 640395  -  make bkradd does not work (bpeck@redhat.com)
- 617274 - Owner field should be mandatory (dcallagh@redhat.com)
- 736989 - fix bkr distros-list --treepath (dcallagh@redhat.com)
- 734535 - beaker-transfer query used on scheduler is inefficient.
  (bpeck@redhat.com)
- 734850 - beaker-watchdog run method doesn't handle exceptions
  (bpeck@redhat.com)
- 569909 - Add user SSH public keys (stl@redhat.com)
- 728394 - bkr client command for testing harness installation
  (dcallagh@redhat.com)
- 713578 - Filter matrix job by multiple whiteboards. (rmancy@redhat.com)
- 733966 - Initial version of check script for beaker server
  (rmancy@redhat.com)

- Added: Environment and RhtsOptions to metadata (mcsontos@redhat.com)
- workflow-xslt: Implement support for boolean arguments (davids@redhat.com)
- after importing distros run beaker-repo-update (bpeck@redhat.com)
- fix for beaker labcontroller task (bpeck@redhat.com)
- Enhanced ausearch. (mcsontos@redhat.com)
- Added: CompatService to RhtsOptions (mcsontos@redhat.com)

* Wed Sep 14 2011 Bill Peck <bpeck@redhat.com> 0.7.1-2
- 738319 when importing distros osminor doesn't enforce a string
  (bpeck@redhat.com)

* Wed Sep 07 2011 Raymond Mancy <rmancy@redhat.com> 0.7.1-1
- 721383 - Beaker displays many duplicate distro families in Excluded
  Families tab. (bpeck@redhat.com)
- 694351 - Add rotating log files to beaker-server (rmancy@redhat.com)
- 729173 - Redirect to system page after changing owner (stl@redhat.com)
- 730188 - system search by hypervisor (dcallagh@redhat.com)
- 730858 - Instructions for using addDistro (rmancy@redhat.com)
- 617274 - record owner and uploader for tasks (dcallagh@redhat.com)
- 624417 - record task priority, and return owner and priority in
  Task.to_dict() (dcallagh@redhat.com)
- 729750 - Workaround for RHEL5.3 EUS support (bpeck@redhat.com)
- 733546 - Fix apache from using beakerd principal (rmancy@redhat.com)
- 730321 - Owners can self loan systems again, and take. (rmancy@redhat.com)
- 734525 - default.conf has wrong default value (bpeck@redhat.com)
- 733968 - Get krb_auth value from config, rather han have it hardcoded to
  True. (rmancy@redhat.com)
- 731691 - don't catch exceptions in bkr (dcallagh@redhat.com)
- 730983 - handle duplicate notify cc addresses in job xml
  (dcallagh@redhat.com)
- 728227 - bkr task-list fails for nonexistent package (dcallagh@redhat.com)
- 726363 - Change Job complete mail subject format. Add related test case.
  (ryang@redhat.com)
- 729156 - clean up joins in needpropertyxml (dcallagh@redhat.com)

- 728022 - add ability to filter distros that belong to a specific lab
  controller (dcallagh@redhat.com)
- 734669 - message_bus now uses the config from it's own service, not
  message_bus.conf (rmancy@redhat.com)
- 732789 - Return system that has no LC (rmancy@redhat.com)
- 617274 - catch all exceptions when uploading tasks (dcallagh@redhat.com)
- 729257 - fix parsing of Destructive field in testinfo, 
  populate destructive flag for tasks (dcallagh@redhat.com)
- 624417 - correctly handle missing uploader in Task.to_dict()
  (dcallagh@redhat.com)
- 710524 - remove --nowait option.  Doesn't make sense. (bpeck@redhat.com)

- workflow-xslt: Added support for tag lists (davids@redhat.com)
* Mon Aug 22 2011 Raymond Mancy <rmancy@redhat.com> 0.7.0-1
- This change adds the basic infrastructure into beaker to work with qpid. It
  does this by creating a service that listens on address that can be defined
  in the message_bus module and by creating classes that make it easy to send
  msgs to predefined address. These address (for both listening and sending
  services) are easily added to the code and then inserted/removed into the
  config as they are needed. (rmancy@redhat.com)


* Wed Aug 10 2011 Raymond Mancy <rmancy@redhat.com> 0.6.17-1
- 723753 - system search submits to wrong URL on /available, /free, /mine
- 727692 - Re-added beaker-init command into docs (rmancy@redhat.com)
 (dcallagh@redhat.com)
- 723789 - avoid using deepcopy on xml.dom.minidom nodes
 (dcallagh@redhat.com)
- 655837 - fix cloning multiple child nodes in <hostRequires/> and
 <partitions/> (dcallagh@redhat.com)
- 725807 - move expire_distros from cron.daily to cron.hourly
 (bpeck@redhat.com)
- 572842 - Test program interface to access console logs (bpeck@redhat.com)
- 720715 - re-scan lab controller distros will delete all distros
 (bpeck@redhat.com)
- 720046 - Show power commands in system history tab (stl@redhat.com)
- 725465 - Filter tasks by destructiveness (bpeck@redhat.com)
- 720591 - ensure all bkr subcommands exit with non-zero status on error
 (dcallagh@redhat.com)
- 728110 - Log an entry to system history upon being marked broken
 (stl@redhat.com)
- 722367 - Abort when no harness repo exists. (rmancy@redhat.com)
- 723573 - Change Loan feature (rmancy@redhat.com)
- 723283 - beaker-watchdog should handle exceptions better (bpeck@redhat.com)

- /distribution/beaker/setup: MYSQL_EXTRA_CONFIG env var (dcallagh@redhat.com)
- /distribution/beaker/setup: basepath.harness missing from config
 (dcallagh@redhat.com)
- /distribution/beaker/setup: need harness dir to exist (dcallagh@redhat.com)
- report Warn when reserve limit is exceeded. (bpeck@redhat.com)
- fix uncaught exception handling in beakerd (dcallagh@redhat.com)
- include pmtools in inventory rpm (bpeck@redhat.com)
- fix typo in tests (dcallagh@redhat.com)
- s/mkdir/makedirs/ to create parent dirs also (dcallagh@redhat.com)
- need to use UTC today instead of local today (dcallagh@redhat.com
* Wed Jul 27 2011 Raymond Mancy <rmancy@redhat.com> 0.6.16-1
- 720890 - log uncaught exceptions in beakerd worker threads
  (dcallagh@redhat.com)
- 720248 - link to rpm on task page (dcallagh@redhat.com)
- 720041 - include whiteboard in subject of job completion notifications
  (dcallagh@redhat.com)
- 722387 - soft limits ignored (mcsontos@redhat.com)
- 589036 - man pages for bkr client (dcallagh@redhat.com)
- 720559 - update bkr task-list to handle dict returned from tasks.filter
  (dcallagh@redhat.com)
- 722321 - Beaker scheduler should honor acl's even on admin jobs.
  (bpeck@redhat.com)
- 720044 - Only mark a system broken once (stl@redhat.com)

- Max out the number of time for both the script and argument passed in.
  (jburke@redhat.com)
- Avoid IndexError if getdriver.sh returns only one line (stl@redhat.com)
- move integration tests into their own subpackage (dcallagh@redhat.com)
- move existing client tests to integration tests package (dcallagh@redhat.com)
- Newer RHEL5 automount works correctly now.  No need to use fakenet anymore.
  (bpeck@redhat.com)
- Don't raise an exception on unrecognised attributes from inventory script
  (stl@redhat.com)
* Wed Jul 13 2011 Raymond Mancy <rmancy@redhat.com> 0.6.15-1
- bz717500 - apply timeout to all ProxyHelper subclasses (dcallagh@redhat.com)
- bz718234 - ignore xen distros (bpeck@redhat.com)
- bz718251 - osversion.trigger adds empty tags (bpeck@redhat.com)
- bz717718 - rhts_post snipped for adding Distro repo has bugs
  (bpeck@redhat.com)
- bz717424 - remove distro from all lab controllers when removed from primary
  mirror (dcallagh@redhat.com)
- bz718313 - harness can run next recipe on the previous install
  (bpeck@redhat.com)
- bz720103 - Power command queue thread dying (stl@redhat.com)

- fix cached package check in repo_update.py (dcallagh@redhat.com)
- Better logging for command queue processing (stl@redhat.com)
- Disable re-scan on lab controllers until bz720715  is fixed.
  (bpeck@redhat.com)
- <hostRequires/> is not optional (dcallagh@redhat.com)
- kvm kernel module isn't always available, resulting in inventory task failure
  (stl@redhat.com)

* Tue Jul 12 2011 Bill Peck <bpeck@redhat.com> 0.6.14-10
- Disable re-scan link until bz720715 is fixed. (bpeck@redhat.com)

* Mon Jul 11 2011 Bill Peck <bpeck@redhat.com> 0.6.14-9
- Additional logging for power queue and possible fix for traceback.
  (bpeck@redhat.com)
* Mon Jul 11 2011 Steven Lawrance <stl@redhat.com> 0.6.14-8
- Better logging for command queue processing (stl@redhat.com)

* Tue Jul 05 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.14-7
- 718902 set distro.virt=True for xen distros (dcallagh@redhat.com)

* Thu Jun 30 2011 Bill Peck <bpeck@redhat.com> 0.6.14-6
- don't assume tree_name is defined, add extra checks for addDistro command
  (bpeck@redhat.com)

* Thu Jun 30 2011 Bill Peck <bpeck@redhat.com> 0.6.14-5
- paper bag release (bpeck@redhat.com)

* Thu Jun 30 2011 Bill Peck <bpeck@redhat.com> 0.6.14-4
- KeyError: 'tags' fixed in osversion.trigger (bpeck@redhat.com)

* Thu Jun 30 2011 Bill Peck <bpeck@redhat.com> 0.6.14-3
- Can't return None with xmlrpc. (bpeck@redhat.com)

* Thu Jun 30 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.14-2
- handle hypervisor=None from inventory scripts (dcallagh@redhat.com)

* Wed Jun 29 2011 Raymond Mancy <rmancy@redhat.com> 0.6.14-1
- 711960 - log to stderr in server command-line tools (dcallagh@redhat.com)
- 713254 - make the ORM cascade Provision(Family) deletions to child rows
  (dcallagh@redhat.com)
- 664482 - prevent changing lab controller while a system is in use
  (dcallagh@redhat.com)
- 715243 - include reporter in cc list for system problem reports
  (dcallagh@redhat.com)
- 714974 - Add Hypervisor to System (bpeck@redhat.com)
- 618278 - Create a queue for system commands (stl@redhat.com)
- 715136 - Simpler setup of lab controller (bpeck@redhat.com)

- 715133 - can't access system.id attribute after it is detached,
  sqlalchemy won't accept strings for Boolean columns anymore,
  session.get() is removed,
  manual transaction management not necessary here,
  ensure we roll back any changes on XML-RPC failure,
  avoid leaking half-populated recipes into the database,
  avoid leaking recipes without a recipeset during tests
  (dcallagh@redhat.com)

- Using our new patched TG (rmancy@redhat.com)
- Update selenium version (bpeck@redhat.com)
- pass bool values instead of strings to the database for User.disabled
  (dcallagh@redhat.com)
- handle reporter=None in system_problem_report() (dcallagh@redhat.com)
* Thu Jun 16 2011 Bill Peck <bpeck@redhat.com> 0.6.13-3
- HotFix for looking up users. (bpeck@redhat.com)

* Wed Jun 15 2011 Raymond Mancy <rmancy@redhat.com> 0.6.13-2
- Add upgrade note to remove cfg line, and remove line from dev.cfg
  (rmancy@redhat.com)

* Wed Jun 15 2011 Raymond Mancy <rmancy@redhat.com> 0.6.13-1
- 708172 - allow inventory to update memory even when it is already set
  (dcallagh@redhat.com)
- 709883 - Stops systems with exluded arch's being listed on reserve page.
  (rmancy@redhat.com)
- 710182 - upgrade notes for fixing inconsistent system_status_durations
  (dcallagh@redhat.com)
- 711218 - Don't show recipe tasks from deleted jobs (rmancy@redhat.com)
- 590033 - don't show invalid tasks in bkr task-list (dcallagh@redhat.com)
- 709364 - add Piwik javascript (dcallagh@redhat.com)
- 699974 - Enable groups to edit product and retention tag
  (rmancy@redhat.com)
- 697385 - include more X- headers in broken system notifications
  (dcallagh@redhat.com)
- 709853 - Loaned machine sno longer show up as 'Reserve Now'
  (rmancy@redhat.com)
- 703885 - RFE: Temporarily disable specific Beaker users (bpeck@redhat.com)
- 709883 - simplify and fix Distro.all_systems (dcallagh@redhat.com)
- 709815 - bkr distros-list --limit 10 does not always show 10
  (bpeck@redhat.com)
- 711674 - rhts-compat not working on Fedora 15 (bpeck@redhat.com)

* Wed Jun 01 2011 Raymond Mancy <rmancy@redhat.com> 0.6.12-1
- 706435 - apply datetime localisation to DOM elements inserted by jQuery
  (dcallagh@redhat.com)
- 703548 - hide system cc field from non-owners (dcallagh@redhat.com)
- 705401 - Not detecting Panic on Xen systems (bpeck@redhat.com)
- 704948 - beaker-proxy init script is half broken (bpeck@redhat.com)
- 703841 - bkr workflow-simple --prettyxml should imply --debug
  (bpeck@redhat.com)
- 700790 - no way how to get email associated with user (bpeck@redhat.com)
- 704563 - Changed log_delete tobe able to handle random exceptions, as well
  as ensuring that it can delete all the right directories even if they are in
  unexpected locations (rmancy@redhat.com)
- Adding xmlrpc logging to the server ala proxy (rmancy@redhat.com)
- Log kickstart pre/post to console (mcsontos@redhat.com)

* Fri May 20 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.11-2
- 706150 do not activate InstallOptions js when widget is read-only
  (dcallagh@redhat.com)

* Wed May 18 2011 Raymond Mancy <rmancy@redhat.com> 0.6.11-1
- 694107 - remove paginate limit for systems (dcallagh@redhat.com)
- 572835 Test program interface to install debuginfo.
  (bpeck@redhat.com)
- 701414 - obey system provision options in XML-RPC (dcallagh@redhat.com)
- 702106 - update for new repo layout on repos.fedorapeople.org
  (dcallagh@redhat.com)
- 702082 - push/legacypush should not attempt to create new systems and  
  /distribution/inventory: fix Numa info when not supplied by smolt (dcallagh@redhat.com)
- 599701 - allow searching by system serial number (dcallagh@redhat.com)
- 703497 - remove lagacy rhts support from kickstarts (bpeck@redhat.com)
- 645873 - Job cancelled soon after creation doesn't terminate
  (bpeck@redhat.com)
- 541291 - Can't add per-minor-release install options (bpeck@redhat.com)
- 704374 - AlphaNavBar widget should sort letters (dcallagh@redhat.com)
- 590033 - [RFE] removing tasks from task library (bpeck@redhat.com)
- 702665 - bkr workflow-simple tasks can get out of order (bpeck@redhat.com)
- 658515 - javascript to adjust datetimes to local timezone
  (dcallagh@redhat.com)
- 692935 - Remove lab controllers (rmancy@redhat.com)
- 636565 - RFE: needs install machine only with @base group
  (bpeck@redhat.com)
- 705428 - repo_update.py: bypass local cache for package files
  (dcallagh@redhat.com)

- show a less scary message when motd does not exist (dcallagh@redhat.com)
- Disable CHECKRECIPE until kickstarts are fixed. (bpeck@redhat.com)
- remove tg.include_widgets from server.cfg. (bpeck@redhat.com)
- fix osversion install options js (dcallagh@redhat.com)
- Add Xvfb to Requires. (bpeck@redhat.com)
- Add firefox to Requires as well. (bpeck@redhat.com)
- still more Requires (bpeck@redhat.com)
- Set-up logging to console. (mcsontos@redhat.com)

* Thu May 05 2011 Raymond Mancy <rmancy@redhat.com> 0.6.10-4
- and for commit().... (rmancy@redhat.com)

* Thu May 05 2011 Raymond Mancy <rmancy@redhat.com> 0.6.10-3
- rollback() does not clear the job objects from the session, close() does
  (rmancy@redhat.com)

* Thu May 05 2011 Raymond Mancy <rmancy@redhat.com> 0.6.10-2
- expired_logs() is now a generator, holding 60k+ Job objects in memory was not
  agreeable (rmancy@redhat.com)

* Wed May 04 2011 Raymond Mancy <rmancy@redhat.com> 0.6.10-1
- 698752 osversion.trigger should prefer .treeinfo (bpeck@redhat.com)
- 699935 motd change to .xml instead of .txt. Needs an update in the config
  as well (rmancy@redhat.com)
- 700186 fix updateDistro to not talk directly to scheduler (bpeck@redhat.com)
- 700161 Failure to import task rpm should unlink bad rpm Bug: 700161 Change-Id:
  If0027694c5f5f740ed7e16dd78732a0336ef62cb (bpeck@redhat.com)
- 700675 Take away the Remove link in the LC page for the time being
  (rmancy@redhat.com)
- 700751 Fixed counterintuitive group filter (mcsontos@redhat.com)
- 700761 Set-up logging to console. (mcsontos@redhat.com)

- Ensure recipe log paths have trailing slashes, WebDAV works correctly with this.
  (rmancy@redhat.com)
- We now allow admins to delete their own jobs (rmancy@redhat.com)
- Fix warning generated by log_delete(), also use correct kw arg to find_jobs()
  (rmancy@redhat.com)

* Wed Apr 20 2011 Raymond Mancy <rmancy@redhat.com> 0.6.9-1
- 695970 Limiting job via whiteboard retrieval to max 20. (rmancy@redhat.com)
 
- 681584 make bkradd should fail if trying to upload the same version task. 
  (bpeck@redhat.com)
- 601952 RFE: add filtering by group to job specification XML (bpeck@redhat.com)
- 682602 common utilisation code for reporting (dcallagh@redhat.com)
- 682655 warn about excluded tasks in workflow-simple (dcallagh@redhat.com)
- 691796 make owner mandatory for systems (dcallagh@redhat.com)
    
- 693582 more filter options for utilisation graph (dcallagh@redhat.com)
- 696335 efibootmgr is not just for ia64 anymore (bpeck@redhat.com)
- 692163 bkr machine-test fails due to recent inventory script updates 
 (bpeck@redhat.com)
- 663788 - add updates for Fedora kickstarts during install
 (bpeck@redhat.com)
- 683913 bkr workflow-simple does not handle empty recipes filtered by arch quite well
  First step, move to pre-filter tasks based on arch and osmajor.  Second step,
  turn off post-filtering on scheduler.  Whatever tasks are passed in is what
  will be run (bpeck@redhat.com)
              
- 645662 Change the add distro process to not rely on distro name for method
  (bpeck@redhat.com)
- 688122 - ks-templates: beah services usage [3/3] (mcsontos@redhat.com)
                
- build requires make (dcallagh@redhat.com)
- avoid using real hostnames in test data (dcallagh@redhat.com)
- show crosshair on utilisation graph (dcallagh@redhat.com)
- New beaker import task. (bpeck@redhat.com)
- We now allow admins to delete their own jobs (rmancy@redhat.com)
* Tue Apr 12 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.8-5
- some test fixes (dcallagh@redhat.com)
- fix bug in 0.6.8 system_status_duration upgrade script (dcallagh@redhat.com)

* Thu Apr 07 2011 Bill Peck <bpeck@redhat.com> 0.6.8-4
- Regression in job scheduling when specifying multiple labcontrollers Bug:
  694524 (bpeck@redhat.com)

* Thu Apr 07 2011 Raymond Mancy <rmancy@redhat.com> 0.6.8-3
- 694352 empty <and/> causes sqlachemy to produce invalid SQL (dcallagh@redhat.com)

* Wed Apr 06 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.8-2
- bz693869 - fix up 0.6.7 reservation table population script
  (dcallagh@redhat.com)

* Wed Apr 06 2011 Raymond Mancy <rmancy@redhat.com> 0.6.8-1
- 680497 Graph machine usage over time (utilisation graphs) (dcallagh@redhat.com)
- 651199 remove unneeded ErrorDocument directive from Apache config
  (dcallagh@redhat.com)
- 689344 fs attribute in <partition/> should be optional (dcallagh@redhat.com)
- 679879 Issue: testing using key/value for selection of test host is unreliable 
  (bpeck@redhat.com)
- 693777 ability to set RLIMIT_AS from config file setting (bpeck@redhat.com)
- 678356 Ability to set recipe autopick random (bpeck@redhat.com)
- 691445 Quote all variables or we fail when VARIANT is Empty. (bpeck@redhat.com)
- 690342 /free no longer has loaned machines unless they are loaned to the current
  user and are not currently in use (rmancy@redhat.com)
- 688775 more headers in email for broken system (rmancy@redhat.com)
- 691745 Adding/Removing retention tags actually works now (rmancy@redhat.com)
- 691623 Fix regression introduced where a loaned machined could not be provisioned to
  the loanee if the system has groups and the loanee is not a member of the
  group (rmancy@redhat.com)

* Thu Mar 23 2011 Raymond Mancy <rmancy@redhat.com> 0.6.7-1
- 688122 - ks-templates: beah services usage (mcsontos@redhat.com)
- 685085 Ensure matrix report data is generated from whiteboard (rmancy@redhat.com)
- 680092 Return NumaNode and Group columns in system search (rmancy@redhat.com)
- 683121 Don't expose Distro.install_name only to be used internally (bpeck@redhat.com)
- 684788 Can't return the machine because of active recipe, which is already finished
- 681871 bkr job-submit fails when input XML file contains the xml header (bpeck@redhat.com)
- 659702 Loaned machines available to schedule Update beakerd to not touch loaned machines (bpeck@redhat.com)
- 682313 WebUI missing clone button for recipe. (bpeck@redhat.com)
- 629025 Implement a cap on size and number of files uploaded (bpeck@redhat.com)
- 687995 remove legacy rhts support from /distribution/inventory (bpeck@redhat.com)
- 683003 force hostnames to lowercase (bpeck@redhat.com)
- 671474 Gather more sensible CPU info on S390, PPC, IA64.
- 680324 Remove dependency on anaconda. (stl@redhat.com)
- fix beaker setup task. (bpeck@redhat.com)
- script to populate reservation table (dcallagh@redhat.com)
- introduce a new reservation table (dcallagh@redhat.com)
- remove XML-RPC methods for legacy RHTS (dcallagh@redhat.com)
- test for bug 681143 (dcallagh@redhat.com)
- /distribution/beaker/setup: add missing config entries (dcallagh@redhat.com)
- /distribution/beaker/dogfood: install correct selenium bindings
  (dcallagh@redhat.com)
- cleain up various warnings (dcallagh@redhat.com)
- Use a packaged version of smolt instead of our own. (stl@redhat.com)



* Thu Mar 10 2011 Raymond Mancy <rmancy@redhat.com> 0.6.6-2
- Fix typo in spec (rmancy@redhat.com)

* Wed Mar 09 2011 Raymond Mancy <rmancy@redhat.com> 0.6.6-1
- 679398 freeze header and first column for matrix report (rmancy@redhat.com)
- 676735 Whiteboard filter results are now displayed in desc order (rmancy@redhat.com)
- 678033 Export action for jobs (rmancy@redhat.com)
- 676834 Job Ack/Nak between members of the same group (rmancy@redhat.com)
- 679678 fix up priority attribute on <recipeSet/> (dcallagh@redhat.com)
- 679232 redirect to /forbidden when permissions are insufficient
  (dcallagh@redhat.com)
- 678651 include addDistro.sh in beaker-lab-controller package (bpeck@redhat.com)
- 572833 [RFE] Allow $swapsize to define swapsize (bpeck@redhat.com)
- 681143 make bkradd omits requirements/runfor in Makefile that differ in case
  (bpeck@redhat.com)
- 668473 Jobs left in queued state forever (bpeck@redhat.com)
- 679835 Drop version-release from task rpm names received from Scheduler
  (bpeck@redhat.com)

- 677905 XML-RPC method to return system history (dcallagh@redhat.com)


* Tue Mar 01 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.5-3
- we can only be picky about TurboGears version on RHEL (dcallagh@redhat.com)

* Wed Feb 23 2011 Raymond Mancy <rmancy@redhat.com> 0.6.5-2
- depend on our exact version of TurboGears (dcallagh@redhat.com)
- show identity errors on the login form (dcallagh@redhat.com)

* Wed Feb 23 2011 Raymond Mancy <rmancy@redhat.com> 0.6.5-1
- 678215 SQL instructions for replaceing '' with NULL for recipe.whiteboard
(rmancy@redhat.com)
- 676410 Fix matrix report view (rmancy@redhat.com)
- 674566 show identity errors on the login form (dcallagh@redhat.com)
- 677951 show friendly error for non-existent arch (dcallagh@redhat.com)
- 676092 show all activity on activity page (dcallagh@redhat.com)
- 676093 only admins can add/remove distro tags (dcallagh@redhat.com)
- 663277 test case for login redirect with NestedVariablesFilter (dcallagh@redhat.com)
- 676362 [RFE] bkr job-submit add --combine option to combine multiple jobs
　(bpeck@redhat.com)
- 676091 Only show distros that are on a lab controller. Allow admins to delete
　distros from lab controllers. (bpeck@redhat.com)
- 676947 fix login thread to keep trying, log any exceptions caught.
　(bpeck@redhat.com)
- 676067 Retention_tag and Product can't be passed in on the command line
　(bpeck@redhat.com)
- 602112 When /distribution/install is run check that we are running with correct
　recipe and verify the distro requested was put down. (bpeck@redhat.com)

- add index on activity.created (dcallagh@redhat.com)
- update selenium tests to work with selenium-2.0b2 (dcallagh@redhat.com)
- depend on our exact version of TurboGears (dcallagh@redhat.com)
- remove PAT CPU check. (jburke@bass.usersys.redhat.com)
* Wed Feb 23 2011 Raymond Mancy <rmancy@redhat.com> 0.6.4-4
- fix for cancel and clone links when mounted under /bkr (rmancy@redhat.com)

* Thu Feb 10 2011 Raymond Mancy <rmancy@redhat.com> 0.6.4-3
- Fix so job-delete works with tags/products/family etc (rmancy@redhat.com)

* Sat Feb 09 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.4-2
- bkr workflow-xslt requires libxslt-python (dcallagh@redhat.com)
- package man page for bkr-workflow-xslt (dcallagh@redhat.com)

* Tue Feb 08 2011 Raymond Mancy <rmancy@redhat.com> 0.6.4-1
- bz603982 - Small fix for task search on system page (rmancy@redhat.com)
- bz660480 - deletion code, allowing users to delete jobs (rmancy@redhat.com)
- bz667456 - message of the day (rmancy@redhat.com)
- bz673698 - Fix regression with tasks not showing more than 30
  (rmancy@redhat.com)
- ignore_missing_tasks parameter in job submission (dcallagh@redhat.com)
- report all missing tasks instead of just the first (dcallagh@redhat.com)
- remove Cobbler record for systems when renaming (dcallagh@redhat.com)
- admins should be able to schedule/reserve any system (dcallagh@redhat.com)
- avoid leaking orphaned Recipe objects into the session (dcallagh@redhat.com)
- cascade deletions from system to labinfo (dcallagh@redhat.com)
- Allow lab controllers to be disabled. (bpeck@redhat.com)
- Added detect support for Microsoft's Hyper V and VmWare. (bpeck@redhat.com)
- Added lab_env snippet which can be customized for each lab.
  (bpeck@redhat.com)
- Added a XSLT based workflow - bkr workflow-xslt (davids@redhat.com)

* Fri Jan 28 2011 Raymond Mancy <rmancy@redhat.com> 0.6.3-2
- Fix problem with randrange throwing errors when system.count() is <= 1
  (rmancy@redhat.com)

* Thu Jan 27 2011 Dan Callaghan <dcallagh@redhat.com> 0.6.3-1
- bz613113 - Filter systems by added date (rmancy@redhat.com)
- bz669736 - Remove show all links (rmancy@redhat.com)
- bz654304 - beaker-delete-system script for sysadmins to delete system
  rows (dcallagh@redhat.com)
- make system_id foreign keys not NULLable and cascade
  (dcallagh@redhat.com)
- bz664998 - method in ks_meta doesn't seem to work for custom kickstart
  (bpeck@redhat.com)
- encoding is not allowed in Vim modelines since 7.3 (should be
  fileencoding) (dcallagh@redhat.com)
- bz671233 - record elapsed time spent executing method
  (bpeck@redhat.com)
- bz670868 - We can't set allow_none on the version of python we need to
  support. (bpeck@redhat.com)
- bz669427 - Added kernel_options_post to default workflow options.
  (bpeck@redhat.com)
- bz666981 - Dry run for nag email (rmancy@redhat.com)
- bz668314 - add NUMA nodes to system search (dcallagh@redhat.com)
- bz662909 - add server deps to BuildRequires, so that sphinx autodoc
  works (dcallagh@redhat.com)
- python-sphinx10 does not exist in Fedora 14 and higher
  (dcallagh@redhat.com)

* Wed Jan 12 2011 Raymond Mancy <rmancy@redhat.com> 0.6.2-1
- bz663114 - Move cancel features from Recipe to RecipeSet (rmancy@redhat.com)
- bz662703 - Product list sorted and test (rmancy@redhat.com)
- bz659804 - cache some results from sqla (rmancy@redhat.com)
- bz660529 - better XML-RPC fault strings when login is required (dcallagh@redhat.com)
- bz660491 - store proxying service's username as the service for activity records
  store proxying service in the visit_identity row (dcallagh@redhat.com)
- bz665441 - legacy_push: don't touch keys which were not pushed (dcallagh@redhat.com)
- bz660527 - use Referer if forward_url parameter is not passed to /login
  (dcallagh@redhat.com)
- bz6200292 - Fixes endless redirect, as well as loading task page by task name
  (rmancy@redhat.com)
- bz620967 - Fix for comments to work in chrome (rmancy@redhat.com)
- bz660488 - use ENGINE=InnoDB in MySQL (dcallagh@redhat.com)
- bz660532 - check distro for suitability in systems.provision XML-RPC method
  (dcallagh@redhat.com)
- bz624857 - validate fqdn when updating system details (dcallagh@redhat.com)
- force workflows to use nfs based distro.  this is only needed until we get
  rid of the ftp and http imports in cobbler (bpeck@redhat.com)
- add python-kid to BuildRequires (dcallagh@redhat.com)

* Wed Jan 05 2011 Bill Peck <bpeck@redhat.com> 0.6.1-5
- Don't call update_status() after every result reported.  Wait for the task to
  finish before pushing the results up the tree. (bpeck@redhat.com)
- Revert "some fixes for correctly doing equality with the cached objects"
  (bpeck@redhat.com)

* Tue Jan 04 2011 Bill Peck <bpeck@redhat.com> 0.6.1-4
- disable cache due to session issues: (bpeck@redhat.com)

* Tue Jan 04 2011 Bill Peck <bpeck@redhat.com> 0.6.1-3
- fix glob to grab all test data. (bpeck@redhat.com)
- some fixes for correctly doing equality with the cached objects
  (rmancy@redhat.com)
- Previous update_status model will fall down with very large jobs.
  (bpeck@redhat.com)
- bz659804 - cache some results from sqla (rmancy@redhat.com)
- Added test_update_status unit test. Also added some helpers to data_setup
  Modified beaker/dogfood test to take optional arguments. (bpeck@redhat.com)

* Fri Dec 17 2010 Dan Callaghan <dcallagh@redhat.com> 0.6.1-2
- Bug 663111 - proxy.log being rotated with every line of output
  (bpeck@redhat.com)
- Bug 662214 - Add timeout of 120 seconds to kobo.  Should keep us from
  hanging forever. (bpeck@redhat.com)

* Tue Dec 14 2010 Dan Callaghan <dcallagh@redhat.com> 0.6.0-3
- bz662799 - beaker-transfer needlessly logins (bpeck@redhat.com)

* Fri Dec 10 2010 Raymond Mancy <rmancy@redhat.com> 0.6.0-2
- bz661665 - fixes for job-result for tasks and a bad attempt at tests
  (rmancy@redhat.com)
- bz661652 - avoid creating orphan recipe_task rows (dcallagh@redhat.com)

* Tue Dec 09 2010 Raymond Mancy <rmancy@redhat.com> 0.6.0-1
- bz661307 - beaker-watchdog run transfer_log in separate thread. (bpeck@redhat.com)
- bz660714 -  update log paths in one xmlrpc call (bpeck@redhat.com)
- bz660339 - don't return sub-tasks for task_info (bpeck@redhat.com)
- bz658503 - record changes made by inventory scripts in system history (dcallagh@redhat.com)
- bz634965 - beaker-repo-update, creates/updates harness dir (bpeck@redhat.com)
- bz659141 - Fix cloning RS, also test (rmancy@redhat.com)
- bz658929 - prevent orphaned recipe_task rows (dcallagh@redhat.com)
- bz583165 - install API docs and serve them from apache (dcallagh@redhat.com)
- bz579812 - link to job in notification mail (dcallagh@redhat.com)
- bz638092 - redirect back to /jobs/mine after cancelling a job (dcallagh@redhat.com)
- bz644696 - XML-RPC interface to provision a system,
           better handling of Cobbler template escaping in kickstarts (dcallagh@redhat.com)
- bz644694 - XML-RPC interface to control system power,
           clear_netboot option for systems.power() method (dcallagh@redhat.com)
- bz654931 - edited rng to add ks_appends definition (rmancy@redhat.com)
- bz644691 - XML-RPC interface to release a reserved system (dcallagh@redhat.com)
- bz644689 - XML-RPC interface to reserve a system (dcallagh@redhat.com)
- bz644701 - support "proxy authentication", whereby a user may log in as another user (dcallagh@redhat.com)
- bz644687 - expose Atom feeds for system searches, expose RDF description for systems,
             added API docs for system atom feeds and RDF descriptions (bz644687) (dcallagh@redhat.com)

- must use outerjoins on logs, since a recipe may not have any sub-logs. (bpeck@redhat.com)
- update system.date_modified when importing from CSV (dcallagh@redhat.com)
- update system.date_modified everywhere (dcallagh@redhat.com)
- fix handling of checksum (dcallagh@redhat.com)
- slightly smarter logic for legacypush, to avoid spurious key-value entries in system history (dcallagh@redhat.com)
- use external redirects for /login (dcallagh@redhat.com)
- list-systems and system-details commands for bkr client (dcallagh@redhat.com)
- system-power and system-provision commands for bkr client (dcallagh@redhat.com)
- install inventory RDF schema definition (dcallagh@redhat.com)

* Tue Dec 07 2010 Bill Peck <bpeck@redhat.com> 0.5.63-6
- bz660714 -  update log paths in one xmlrpc call (bpeck@redhat.com)

* Wed Dec 01 2010 Bill Peck <bpeck@redhat.com> 0.5.63-5
- Revert "bz590951 - Using custom repo during system install"
  (bpeck@redhat.com)

* Wed Dec 01 2010 Bill Peck <bpeck@redhat.com> 0.5.63-4
- must use outerjoins on logs, since a recipe may not have any sub-logs.
  (bpeck@redhat.com)

* Wed Dec 01 2010 Raymond Mancy <rmancy@redhat.com> 0.5.63-3
- Needed to remove prod/tag from to_xml() in class RecipeSet
  (rmancy@redhat.com)

* Wed Dec 01 2010 Raymond Mancy <rmancy@redhat.com> 0.5.63-2
- Updated product-update to not print out debug msg (rmancy@redhat.com)

* Tue Nov 30 2010 Bill Peck <bpeck@redhat.com> 0.5.63-1
- Merge branch 'bz590951' into develop (bpeck@redhat.com)
- add --cc command line option to workflows. (bpeck@redhat.com)
- read only tag/product for non owner/admin (rmancy@redhat.com)
- bz654789 - Don't rely on the recipe ending.  Run every hour and transfer what
  matches. (bpeck@redhat.com)
- upgrade notes, moved from 62 to 63 (rmancy@redhat.com)
- bz649483 - Job level product/retentiontag. All working (rmancy@redhat.com)
- bz590951 - Using custom repo during system install (bpeck@redhat.com)

* Thu Nov 25 2010 Raymond Mancy <rmancy@redhat.com> 0.5.62-2
- with rmancy: TestTime with no suffix means seconds (dcallagh@redhat.com)
- fix for reserveworkflow: my_cmp was in the wrong place (dcallagh@redhat.com)

* Wed Nov 24 2010 Raymond Mancy <rmancy@redhat.com> 0.5.62-1
- Experiencing xmlrpc timeouts when talking to cobbler.  - cobbler is stupid
  and doesn't honor the page, results_per_page options.    get_item_names still
  doesn't honor results_per_page but it only transfers the names.  - Of course
  this is stupid on many levels, creating a system record shouldn't force    us
  to select a profile either. (bpeck@redhat.com)
- first go at xmlrpc api docs: auth methods (dcallagh@redhat.com)
- bz647176 - ui for changing system notify cc list (dcallagh@redhat.com)
- bz654299 - configurable distro tag for broken system detection
  (dcallagh@redhat.com)
- bz647176 - RFE: Allow additional e-mail address to be notified when system is
  automatically marked as broken (bpeck@redhat.com)
- bz653513 - Need a replacement for test_lab_machine (bpeck@redhat.com)
- bz654302 - Nag emails will now exclude owner/users and thos eon non shared
  machines (rmancy@redhat.com)
- bz654097  - support for Fedora14 kickstarts (bpeck@redhat.com)
- bz624726 - beaker-proxy and beaker-watchdog init scripts do not create PID
  file (bpeck@redhat.com)
- bz652334 - ensure activity entries are truncated on UTF-8 character
  boundaries (dcallagh@redhat.com)
- bz652298 - don't blindly change the status or type of a system. (bpeck@redhat.com)
- bz634896 - Stop on ParserWarnings and ParserErrors (rmancy@redhat.com)
- bz651418 - fix system grid sorting (dcallagh@redhat.com)
- bz645873 -  Job cancelled soon after creation doesn't terminate
  (bpeck@redhat.com)

* Thu Nov 11 2010 Bill Peck <bpeck@redhat.com> 0.5.61-4
- increase timeout from 20 seconds to 40 seconds. (bpeck@redhat.com)
- bz648497 fix (bpeck@redhat.com)
- fixed changelogs (rmancy@redhat.com)

* Thu Nov 11 2010 Raymond Mancy <rmancy@redhat.com> 0.5.61-3
- Hack for Key/Value without MODULE now we aren't using XMLRPC call to get list
  (rmancy@redhat.com)

* Thu Nov 11 2010 Raymond Mancy <rmancy@redhat.com> 0.5.61-2
- Merge branch 'release-0.5.60' into release-0.5.61 to ensure all changes from 60-2 are brought in (rmancy@redhat.com)
* Thu Nov 11 2010 Raymond Mancy <rmancy@redhat.com> 0.5.61-1
- bz644132 - Speed up searchbar (rmancy@redhat.com)
- bz650300 - require login for reporting system problems (dcallagh@redhat.com)
- bz598781 - To deterministic in host selection (bpeck@redhat.com)
- bz648497 - Jobs don't run always when free systems available.   
             When picking recipe.systems don't filter out systems from labs 
             that don't have the distro yet. Update the Queued to Schedule code to
             filter out systems from labs that don't have the distro (bpeck@redhat.com)
- bz649179 - show friendly error message when unparseable job xml is submitted
  (dcallagh@redhat.com)
- bz640395 - make bkradd work (bpeck@redhat.com)
- bz648527 - Now admins get 'Schedule provision' when they are looking at a
  machine that is being used (rmancy@redhat.com)
- bz646520 - Retention feature was added without allowing cmdline option.  Also
  fixed bkr.client helpers to allow setting the guestname in guest recipes.
  (bpeck@redhat.com)
- bz647854 - Manual machine with a group will not ISE when viewed by non logged
  in user (rmancy@redhat.com)
- bz647566 - cascade key type deletions correctly (dcallagh@redhat.com)
- bz647292 - fix up broken system detection to handle the case where a system's
  status has never changed (dcallagh@redhat.com)

* Thu Nov 04 2010 Bill Peck <bpeck@redhat.com> 0.5.60-3
- quick hack to disable Key/Value -> Module search. (bpeck@redhat.com)

* Thu Oct 28 2010 Bill Peck <bpeck@redhat.com> 0.5.60-2
- fix missing upload and basepath when cache is off. (bpeck@redhat.com)

* Thu Oct 28 2010 Raymond Mancy <rmancy@redhat.com> 0.5.60-1
- bz635611 - specific machine jobs haven't got higher priority than no machine
  specific ones (bpeck@redhat.com)
- bz632583 - Can loan system when system has user (rmancy@redhat.com)
- bz634832 - Have to be logged in to add task now (rmancy@redhat.com)i
- bz568331 - Beaker logo now links to root dir (rmancy@redhat.com)
- bz639171 - Added some Ajax spinners to the following: Reserve, Workflow, Task Search, Job Whiteboard, Ack/Nak recipe, Priority, Retention Tag (rmancy@redhat.com)
- bz632675 - Re-architect beaker results reporting/storage (bpeck@redhat.com)
- bz638092 - redirect to /jobs/mine after submitting a new job (dcallagh@redhat.com)
- bz646046 - Enable option to force distro update in osversion.trigger (rmancy@redhat.com)
- bz645635 - Some tests to check csv export privacy (rmancy@redhat.com)
- bz638790 - add <guestrecipe/> definition to job xml schema (dcallagh@redhat.com)
- bz642104 - descriptive text for system lender field (dcallagh@redhat.com)
- bz638790 - use RELAX NG instead of XML Schema for validationg job xml (dcallagh@redhat.com)
- bz642122 - include link to system and some system information in problem
             report e-mail and brokenness notifications (dcallagh@redhat.com)

- bz643498 - Fixed 'less than' operator with Key/Value (rmancy@redhat.com)
- bz643381 - beakerd ERROR Failed to commit due to :list.remove(x): x not in
             list (bpeck@redhat.com)

* Tue Oct 19 2010 Bill Peck <bpeck@redhat.com> 0.5.59-3
- HOTFIX bz643381 beakerd ERROR Failed to commit due to
  :list.remove(x): x not in list (bpeck@redhat.com)

* Thu Oct 14 2010 Raymond Mancy <rmancy@redhat.com> 0.5.59-2
- hotfix - Cloned jobs with ack/nak were failing due to having response in the
  xml.          removed this attribute when cloning (rmancy@redhat.com)

* Wed Oct 13 2010 Raymond Mancy <rmancy@redhat.com> 0.5.59-1
- bz634571 - add response ack/nak into returned resipset xml if it exists
  (rmancy@redhat.com)
- bz636212 - update command line to use ks_meta="method=" for install method.
  (bpeck@redhat.com)
- bz467486 - New job delete (rmancy@redhat.com)
- bz638003 - Users with higher privs can now schedule as well as take
- bz618859 - make job whiteboard editable (dcallagh@redhat.com)
- bz627281 - need to clear task types when uploading (dcallagh@redhat.com)
- bz637260 - mark systems which have a run of aborted jobs as broken
  (dcallagh@redhat.com)
- bz589325 - Failed to provision recipeid 8, 'No watchdog exists for recipe 8'
  (bpeck@redhat.com)
- bz600353 - limit arch for releases (bpeck@redhat.com)
- bz641016 - fix bkr errata-workflow cuts erratas names  (bpeck@redhat.com)
- bz634485 -  fix can't use beaker's workflow-autofs to submit subtask (bpeck@redhat.com)

* Fri Oct 01 2010 Bill Peck <bpeck@redhat.com> 0.5.58-3
- beaker-watchdog monitor key needs to include the recipeid to keep us
  from monitoring the wrong recipe.
- remove recipe_taskid from watchdog list, we won't always have one. (bpeck@redhat.com)

* Wed Sep 29 2010 Raymond Mancy <rmancy@redhat.com> 0.5.58-2
- minor fixes for beaker-watchdog.

* Wed Sep 29 2010 Raymond Mancy <rmancy@redhat.com> 0.5.58-1
- Added downgrade instructions to upgrade txt (rmancy@redhat.com)
- we don't transform installPackage and we leave the invalid attribute
  testrepo. (rmancy@redhat.com)
- Change to xsd which allows elements to be in no particular order
  (rmancy@redhat.com)
- completeDays args passed to job-list is now exclusive, rather than inclusive
  also not allowing integer's less than 1 into completeDays (rmancy@redhat.com)
- update specfile to bundle new upgrade notes files (which are .txt instead of
  .sql) (dcallagh@redhat.com)
- fix bad merge (bpeck@redhat.com)
- Merge branch 'bz636651' into develop (rmancy@redhat.com)
- bz631971 - prototype now showing in reserve_systems (rmancy@redhat.com)
- bz634033 - Remove machines from reserve report that have ben reserved via
  RHTS (rmancy@redhat.com)
- Merge branch 'develop' of ssh://rmancy@git.fedorahosted.org/git/beaker into
  develop (rmancy@redhat.com)
- Merge branch 'bz629888' into develop (rmancy@redhat.com)
- Test for taking systems (rmancy@redhat.com)
- bz629888 - group member can now take (rmancy@redhat.com)
- fix typo in /report_problem error message (dcallagh@redhat.com)
- add new retention_tag attribute to XSD (dcallagh@redhat.com)
- avoid duplicate group names (dcallagh@redhat.com)
- fix some unicode SAWarnings which were annoying me (dcallagh@redhat.com)
- Merge branch 'selenium-tests' into develop (dcallagh@redhat.com)
- Merge branch 'bz591652' into develop (dcallagh@redhat.com)
- Merge branch 'bz612227' into develop (dcallagh@redhat.com)
- if RecipeSet has a constructor, it has to explicitly handle any args passed
  to it (super() does not invoke the sqlalchemy magic) (dcallagh@redhat.com)
- this file is replaced by upgrade_0.5.58.txt (dcallagh@redhat.com)
- Fixed up SQL alter table, removed create tables as they are redundant
  (rmancy@redhat.com)
- Added ability to change colspan of retention and priority cols
  (rmancy@redhat.com)
- Fix problem with RecipeSet __init__ and RetentionTag __init__ and table
  schema (rmancy@redhat.com)
- Merge branch 'bz595801' into develop (rmancy@redhat.com)
- bz595801 - This is the first go at adding retention tags. Admins can add and
  change default settings. They are picked up in recipesets,            There
  is an interface in the jobs page to change the retention tag. Also job-list
  is a valid command            which will list jobs by family,tag,number of
  days complete for, or any combination of these. (rmancy@redhat.com)
- bz620605 - Introduction of Automated status (rmancy@redhat.com)
- Automatic commit of package [beaker] release [0.5.56-1]. (rmancy@redhat.com)
- bz593560 - Do over of the reserve report filter. (rmancy@redhat.com)
- additional logging (bpeck@redhat.com)
- only ask the scheduler for active and expired watchdogs every 60 seconds.
  (bpeck@redhat.com)
- don't call parent __init__ on Monitor class. (bpeck@redhat.com)
- apparently gettext gives us a lazystring which has to be coerced to a real
  type (weird) (dcallagh@redhat.com)
- there is no cherrypy.request in beakerd, so we have no nice way of producing
  an absolute url (dcallagh@redhat.com)
- minor chnage.  show debug line before sleep. (bpeck@redhat.com)
- don't remove the monitor in the expired watchdog code. (bpeck@redhat.com)
- Merge branch 'bz634702' into develop (bpeck@redhat.com)
- bz636651 - re-structure beaker-watchdog to not fork a separate process per
  recipe. (bpeck@redhat.com)
- the tree_path will not be available if the distro has been expired from the
  lab. (bpeck@redhat.com)
- bz591652 - automatically mark systems as broken if cobbler task fails
  (dcallagh@redhat.com)
- selenium test for bz612227 XSD validation warning (dcallagh@redhat.com)
- Merge branch 'bz612227' into selenium-tests (dcallagh@redhat.com)
- add python-lxml to Requires for Server and Client (using it for XSD
  validation) (dcallagh@redhat.com)
- bz612227 - validate against XSD in bkr job-submit (dcallagh@redhat.com)
- bz612227 - warn users before accepting job XML which does not validate
  (dcallagh@redhat.com)
- bz612227 - evaluate hostRequires at job submission time, to catch errors in
  XML (dcallagh@redhat.com)
- can catch multiple exception classes, instead of repeating the except clause
  (dcallagh@redhat.com)
- some additions to .gitignore (dcallagh@redhat.com)
- use %%(package_dir)s for static locations, so that we can run from a working
  copy or a system-wide install (dcallagh@redhat.com)
- change selenium install location to /usr/local/share/selenium
  (dcallagh@redhat.com)
- Merge branch 'develop' into selenium-tests (dcallagh@redhat.com)
- Record the last time osversion.trigger ran so we can only process new distros
  (bpeck@redhat.com)
- link=Groups locator is ambiguous, use an xpath instead (dcallagh@redhat.com)
- Merge branch 'bz629422' into develop (dcallagh@redhat.com)
- Merge branch 'bz631421' into develop (dcallagh@redhat.com)
- Merge branch 'bz623603' into develop (dcallagh@redhat.com)
- moved ReportProblemForm widget into bkr.server.widgets, added missing super()
  call (dcallagh@redhat.com)
- a bunch of fiddling, to get all the tests to pass (yay!)
  (dcallagh@redhat.com)
- execute SQL through sqlalchemy instead of MySQLdb directly, in order to re-
  use config etc (dcallagh@redhat.com)
- create_user was breaking my tests, changed it. Still seems to be breaking
  stuff. will look at later (rmancy@redhat.com)
- Merge branch 'develop' into selenium-tests (dcallagh@redhat.com)
- Some of the selenium tests (rmancy@redhat.com)
- Merge branch '634247' into develop (bpeck@redhat.com)
- Merge branch 'bz633885' into develop (bpeck@redhat.com)
- Merge branch 'master' into develop (bpeck@redhat.com)
- fix except code to handle cobbler xmlrpc errors. (bpeck@redhat.com)
- only package up the consolidated upgrade_xxx.sql scripts. (bpeck@redhat.com)
- bz629422 - disable TurboGears scheduler (dcallagh@redhat.com)
- oops, update_data is deprecated (update_params is what I meant)
  (dcallagh@redhat.com)
- selenium test for bz623603 (dcallagh@redhat.com)
- Merge branch 'bz623603' into selenium-tests (dcallagh@redhat.com)
- full path to bkr.timeout_xmlrpclib. (bpeck@redhat.com)
- update spec file to include timeout_xmlrpclib.py (bpeck@redhat.com)
- add missing timeout code. (bpeck@redhat.com)
- add timeout_xmlrpclib.ServerProxy() to keep us from getting stuck.
  (bpeck@redhat.com)
- Merge branch 'develop' of ssh://git.fedorahosted.org/git/beaker into develop
  (bpeck@redhat.com)
- added sql upgrade commands for 0.5.56->0.5.57. (bpeck@redhat.com)
- selenium test for bz631421 (dcallagh@redhat.com)
- Merge branch 'bz631421' into selenium-tests (dcallagh@redhat.com)
- set page title correctly in form-post.kid (dcallagh@redhat.com)
- bz631421 - fix page title for systems (dcallagh@redhat.com)
- bz623603 - allow users to report a problem with a system
  (dcallagh@redhat.com)
- depend on TurboMail >= 3.0, v2.0 doesn't work (dcallagh@redhat.com)
- unit test for bz612227 (dcallagh@redhat.com)
- Merge branch 'bz612227' into selenium-tests (dcallagh@redhat.com)
- bz612227 - evaluate hostRequires at job submission time, to catch errors in
  XML (dcallagh@redhat.com)
- can catch multiple exception classes, instead of repeating the except clause
  (dcallagh@redhat.com)
- create admin user when initialising db (this fixes test_add_user.py)
  (dcallagh@redhat.com)
- read from subprocesses line-at-a-time, to ensure lines don't get buffered
  across test boundaries (dcallagh@redhat.com)
- tests need to be not executable, otherwise nose will skip them
  (dcallagh@redhat.com)
- this particular test can reuse firefox sessions, to save time
  (dcallagh@redhat.com)
- reader thread, to allow nose to capture subprocesses' stdout
  (dcallagh@redhat.com)
- use unicode objects to keep sqlalchemy happy (dcallagh@redhat.com)
- declare selenium client as a test dependency (dcallagh@redhat.com)
- introduced new data_setup module for setting up test data; using that for
  thorough, repeatable, passing selenium tests for recipe data grid
  (dcallagh@redhat.com)
- Merge branch 'bz629147' into selenium-tests (dcallagh@redhat.com)
- need to pass kwargs to model constructors (dcallagh@redhat.com)
- the generated SQL comes out differently here if we have configured MySQL as
  the engine (dcallagh@redhat.com)
- cleaned up tests to use correct TurboGears config; eliminated duplicate
  config loading and logging (dcallagh@redhat.com)
- Merge branch 'selenium-tests' of ssh://rmancy@git.fedorahosted.org/git/beaker
  into selenium-tests (rmancy@redhat.com)
- Changes to deal with seting up DB in test mode (rmancy@redhat.com)
- if selenium/beaker is already running, warn and continue (without starting it
  again) (dcallagh@redhat.com)
- oops, forgot to update logger names for package move (dcallagh@redhat.com)
- fixed recipes test to correctly assert ordering for id column
  (dcallagh@redhat.com)
- Merge branch 'bz629147' into selenium-tests (dcallagh@redhat.com)
- wait for beaker and selenium-server to start listening during setup (instead
  of waiting for a hardcoded delay) (dcallagh@redhat.com)
- moved selenium tests into bkr/server/test/selenium; also start beaker-server
  in package setup (dcallagh@redhat.com)
- first go at setting up selenium tests (dcallagh@redhat.com)

* Wed Sep 29 2010 Raymond Mancy <rmancy@redhat.com> 0.5.57-1
- we don't transform installPackage and we leave the invalid attribute
  testrepo. (rmancy@redhat.com)
- Change to xsd which allows elements to be in no particular order
  (rmancy@redhat.com)
- completeDays args passed to job-list is now exclusive, rather than inclusive
- bz631971 - prototype now showing in reserve_systems (rmancy@redhat.com)
- bz634033 - Remove machines from reserve report that have ben reserved via
  RHTS (rmancy@redhat.com)
- Test for taking systems (rmancy@redhat.com)
- bz629888 - group member can now take (rmancy@redhat.com)
- if RecipeSet has a constructor, it has to explicitly handle any args passed
  to it (super() does not invoke the sqlalchemy magic) (dcallagh@redhat.com)
- this file is replaced by upgrade_0.5.58.txt (dcallagh@redhat.com)
- Fixed up SQL alter table, removed create tables as they are redundant
  (rmancy@redhat.com)
- Added ability to change colspan of retention and priority cols
  (rmancy@redhat.com)
- Fix problem with RecipeSet __init__ and RetentionTag __init__ and table
  schema (rmancy@redhat.com)
- bz595801 - This is the first go at adding retention tags. Admins can add and
  change default settings. They are picked up in recipesets,            There
  is an interface in the jobs page to change the retention tag. Also job-list
  is a valid command            which will list jobs by family,tag,number of
  days complete for, or any combination of these. (rmancy@redhat.com)
- only ask the scheduler for active and expired watchdogs every 60 seconds.
  (bpeck@redhat.com)
- bz636651 - re-structure beaker-watchdog to not fork a separate process per
  recipe. (bpeck@redhat.com)
- the tree_path will not be available if the distro has been expired from the
  lab. (bpeck@redhat.com)
- bz591652 - automatically mark systems as broken if cobbler task fails
  (dcallagh@redhat.com)
- bz612227 - validate against XSD in bkr job-submit (dcallagh@redhat.com)
- bz612227 - warn users before accepting job XML which does not validate
  (dcallagh@redhat.com)
- bz612227 - evaluate hostRequires at job submission time, to catch errors in
  XML (dcallagh@redhat.com)
- Record the last time osversion.trigger ran so we can only process new distros
  (bpeck@redhat.com)
- Some of the selenium tests (rmancy@redhat.com)
- fix except code to handle cobbler xmlrpc errors. (bpeck@redhat.com)
- only package up the consolidated upgrade_xxx.sql scripts. (bpeck@redhat.com)
- bz629422 - disable TurboGears scheduler (dcallagh@redhat.com)
- update spec file to include timeout_xmlrpclib.py (bpeck@redhat.com)
- add missing timeout code. (bpeck@redhat.com)
- add timeout_xmlrpclib.ServerProxy() to keep us from getting stuck.
  (bpeck@redhat.com)
* Thu Sep 16 2010 Raymond Mancy <rmancy@redhat.com> 0.5.57-1
- bz620605 - Introduction of Automated status (rmancy@redhat.com)
- fix beaker-watchdog to not leave zombies around. (bpeck@redhat.com)
- break watchdog logging into its own log file. (bpeck@redhat.com)
- Updated server.cfg and beakerd to write to its own log file.
  (bpeck@redhat.com)
- need outer joins here in case there is no associated row (e.g. new jobs won't
  have a system or result yet) (dcallagh@redhat.com)
- Sql required to upgrade already installed DB. (bpeck@redhat.com)
- bz629147 - fix column sorting for recipes (dcallagh@redhat.com)
- bz606862 - use a deeper directory hierarchy for logs (dcallagh@redhat.com)
- bz629272 - fix logic to prevent us from using systems that we no longer have
  access to. (bpeck@redhat.com)
- moved key-value sorting logic from template to widget code
  (dcallagh@redhat.com)
- bz629080 - fix beaker-proxy push method to call proper method.
  (bpeck@redhat.com)
- bz629076 - add not null constraint on watchdog/system_id. (bpeck@redhat.com)
- Support for Arlinton's SystemProfiles. (bpeck@redhat.com)

* Thu Sep 02 2010 Raymond Mancy <rmancy@redhat.com> 0.5.56-1
- bz595360 - Fixed reserve report to not crash mysql (rmancy@redhat.com)
- bz620604 - Removed take for those without the correct permissions.
  (rmancy@redhat.com)
- bz629067 - adds additional logging to beaker-proxy which may help track down
  memory issues. (bpeck@redhat.com)
- bz593606 - support NUMA node count (dcallagh@redhat.com)
- bz628811 - update unit tests for testinfo.py (dcallagh@redhat.com)
- bz627814 - Fixed a couple of typos (rmancy@redhat.com)
- Merge branch 'master' into bz595360 (rmancy@redhat.com)
- bz593560 - Do over of the reserve report filter. (rmancy@redhat.com)
- bz541285 - sort system key/values (dcallagh@redhat.com)

* Thu Aug 26 2010 Raymond Mancy <rmancy@redhat.com> 0.5.55-1
- bz624594 - patch for beaker-clien tto work with kobo >= 0.3 Daniel Mach
  (rmancy@redhat.com)
- bz626648 - console script to clean up visit and visit_identity tables
  (dcallagh) (rmancy@redhat.com)
- bz595360 - Search bar in Reserve report (rmancy@redhat.com)

* Thu Aug 19 2010 Raymond Mancy <rmancy@redhat.com> 0.5.54-1
- bz621284 - Added restrictions to CSV, also fixed a problem with csv not being
  able to write unicode objects (rmancy@redhat.com)
- bz541297 - Invalid users are caught when adding them to groups
  (rmancy@redhat.com)
- bz618249 - Refactoring some code to seperate view from data
  (rmancy@redhat.com)
- bz605310 - Fix ordering in Admin->OSversion and Distro->Family
  (rmancy@redhat.com)
- bz21458 - Dropdown now works when adding groups to a system
  (rmancy@redhat.com)

* Tue Aug 10 2010 Raymond Mancy <rmancy@redhat.com> 0.5.53-1
- allow getFamily() to work with either a distro or family passed from the
  command line. (bpeck@redhat.com)
- as per bz612025 - Updated docs to document how to add groups
  (rmancy@redhat.com)
- bz617444 - We can now see  the memory values that the filter called by the
  Scheduler uses to determine the system has the correct            memory, in
  accordance with hostRequires (rmancy@redhat.com)

* Thu Aug 05 2010 Bill Peck <bpeck@redhat.com> 0.5.52-3
- bump minor release (bpeck@redhat.com)
- fix System.available() to work correctly with group acl's. (bpeck@redhat.com)

* Wed Aug 04 2010 Bill Peck <bpeck@redhat.com> 0.5.52-2
- bump minor release (bpeck@redhat.com)
- revert --default option on %%packages.  Seems to ignore all remaining
  packages. (bpeck@redhat.com)

* Tue Aug 03 2010 Bill Peck <bpeck@redhat.com> 0.5.52-1
- remove uneeded schema upgrades. (bpeck@redhat.com)
- found bug with ks_appends and ks_meta during testing. (bpeck@redhat.com)
- bz616491 - All users have access to power cycle all machines. Added
  confirmation screen for non users of machines (rmancy@redhat.com)
- bz609202 - new bkr command displaying task details 
- bz607937 - new XML-RPC to get metadata (bpeck@redhat.com)
- addHostRequires and addDistroRequires will now take <xml> from a string.  You
  can still pass in an  xml node too. (bpeck@redhat.com)
- bz595642 - RecipeSets can now be cloned instead of Recipes. Also using
  RecipeSetWidget now (rmancy@redhat.com)
- bz610259 - add the ability to provide %%post...%%end to kickstartd from job xml
  (bpeck@redhat.com)
- add whiteboard handlers (bpeck@redhat.com)
- Add missing #slurp to bootloader line. (bpeck@redhat.com)
- bkr-client: added watchdog-show (mcsontos@redhat.com)
- bz612710 - Makes systems available to members of groups that are on the ACL
  for systems. i.e in System->Available, and in Scheduler->Reserve.
  Also consolidated some of the import statements (rmancy@redhat.com)
- update to expire_distros to allow admin to delete distros from command line.
  (bpeck@redhat.com)
- fix for bz617664 -  Manual provisions and automated installs should provide a
  default set of packages (bpeck@redhat.com)
- change default options to not wait.  taskwatcher now uses 30 seconds between
  polls. (bpeck@redhat.com)
- Added job-clone feature. (bpeck@redhat.com)
- bz603719 - Added some text which explains how to add test params into the Job
  XML workflow (rmancy@redhat.com)

* Tue Jul 27 2010 Bill Peck <bpeck@redhat.com> 0.5.51-2
-  fixed syntax error in beakerd.

* Tue Jul 27 2010 Bill Peck <bpeck@redhat.com> 0.5.51-1
- fixed bkr job-submit --convert to use new <partitions/> tag format.
  (bpeck@redhat.com)
- bz617467 - Minor edit, added 'http://' in front of the HUB URL val as it
  needs to be there, also            added in caveat about needed cvs or git
  revisioned task to have 'make tag' work (rmancy@redhat.com)
- bz601367 - lvm based guest images and most likely guest OS lvm filesystem requests 
  not being processed properly by beaker
- Make sure the watchdog point to this recipes system. (bpeck@redhat.com)
  Set the user to None as the very last step. (bpeck@redhat.com)
- Let anaconda install kernel_options_post for us. (bpeck@redhat.com)
- Its possible we already created the repo before.  If so skip.
  (bpeck@redhat.com)
- Change default to package to []. (bpeck@redhat.com)
- fixes bz617364 - System loaned to userA for RHTS is stolen by Beaker Job for
  userB (bpeck@redhat.com)

* Wed Jul 21 2010 Bill Peck <bpeck@redhat.com> 0.5.50-1
- export task_info command to lab controller proxy. (bpeck@redhat.com)
- Create recipe specific repos instead of one giant repo. (bpeck@redhat.com)
  Update to createRepo to update the base repo and copy it to recipe specific.
  This is faster  and allows the entire task repo to be available.
  (bpeck@redhat.com)
  add missing repos dir (bpeck@redhat.com)
- fix possible race condition when starting a new task, normally the running
  task adds in some extra time for the watchdog, this makes sure we do.
  (bpeck@redhat.com)
- bz607176 - does not return exit code different from 0 if --nowait and error
  is present. (bpeck@redhat.com)
- bz609444 - Job id cannot be easily captured by external script
  (bpeck@redhat.com)
- install nag-email script (bpeck@redhat.com)
- bz572226 - WIP for nag email (rmancy@redhat.com)
  minor edits to nag_email. Allow user to specify which service.
  (bpeck@redhat.com)
  fix nag_email logic fix option parsing to assign threshold to an int.
  (bpeck@redhat.com)

* Tue Jul 13 2010 Bill Peck <bpeck@redhat.com> 0.5.49-1
- include schema upgrade script. (bpeck@redhat.com)
- RecipeWidget needs to require JQuery in its javascript list.  This fixes the
  recipe view. (bpeck@redhat.com)
- Fix push inventory to remove old devices. (bpeck@redhat.com)
- Don't give provision or power options to Virtual systems. (bpeck@redhat.com)
- reset excluded_arches and excluded_osmajor.  Otherwise we only add.
  (bpeck@redhat.com)
- default to not wait on power commands (bpeck@redhat.com)
- Now support editing the OSMajor alias from the web page. this finishes the
  fix for    bz600353 - Limiting architectures (releases) in Beaker
  (bpeck@redhat.com)
- Put COPYING in base package, use .tar.gz for package since tito expects that
  (bpeck@redhat.com)
- bz543061 - RHTS client side tools do not work properly in FIPS enabled mode
           - accept empty string as no-digest. (mcsontos@redhat.com)
- no need for .gitattributes anymore (bpeck@redhat.com)
- put in a FIXME comment for the way the Distro caches queries on multiple
  distros (rmancy@redhat.com)
- bz608946 - system/view not working due to error (rmancy@redhat.com)
           - Added rpc definition for multiple_distros from merged branch
           - fixed small error in JS (rmancy@redhat.com)
           - Made rpc calls in reserve_workflow.js to use the correct url
             (rmancy@redhat.com)
           - url() for my paginate grid (rmancy@redhat.com)
           - Ok, I've decided it's a bad idea to specify the full url in the
             widget. Instead I've gone through the templates and made sure that the full
             url path is being specified in there (rmancy@redhat.com)
           - More url() (rmancy@redhat.com)
           - changed a lot of static links to use tg.url() (rmancy@redhat.com)
- bz598878 - reserve more machines in one step (rmancy@redhat.com)
- bz596410 - Job Matrix nack, minus comment and auth feature
             hide/show recipesets that have been nak'd (rmancy@redhat.com)
           - Ack/Nak/NeedsReview panel is shown in Jobs listing, only available
             to owners and admin of Job. Checkbox in matrix view will show/hide nak recipesets.
           - Comments now working (rmancy@redhat.com)
           - Can comment on item before the ack/nak is changed (rmancy@redhat.com)
           - Added css for jquery UI (rmancy@redhat.com)
             (rmancy@redhat.com)

* Wed Jul 07 2010 Bill Peck <bpeck@redhat.com> 0.5.48-1
- new package built with tito

* Tue Jul 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.47-0
- proper release

* Tue Jul 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.46-5
- bz598878, minor update to code to not need split(',')
- bz572798, Missing conditions/events in history view.

* Fri Jul 02 2010 Bill Peck <bpeck@redhat.com> - 0.5.46-3
- added get_arches and get_family xmlrpc calls.
- updated workflow-simple to use get_arches if no arches specified.

* Wed Jun 30 2010 Bill Peck <bpeck@redhat.com> - 0.5.46-2
- fix bz589876 - Job list progress bars should show progress of running recipes

* Wed Jun 30 2010 Bill Peck <bpeck@redhat.com> - 0.5.46-1
- disable panic detection from reserve workflow.
- merged bz607560, fixes NULL powertype.
- merged bz598878, reserve more machines in one step.

* Tue Jun 29 2010 Bill Peck <bpeck@redhat.com> - 0.5.46-0
- bz608621 added sane defaults to bkr distro-list (limit 10)
- use %%packages --default for RHEL6 kickstart
- bz607558 - relax check for %%packages, before we stopped if we saw %%post or %%pre.

* Wed Jun 22 2010 Bill Peck <bpeck@redhat.com> - 0.5.45-1
- fix string compare

* Tue Jun 21 2010 Bill Peck <bpeck@redhat.com> - 0.5.45-0
- fixed job submission where we call lazy_create.  would create dupe package entries.

* Thu Jun 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.44-3
- bz604906 Pagination setting on Distro->Family are a bit funny
- bz605260 [Beaker] Not able to "Loan" a system even though the group has admin perms
- bz604972 Inventory allows reservation of an already reserved machine 
- bz598525 bkr workflow-simple --package not working

* Thu Jun 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.44-1
- fix panic reporting to report on Running task

* Thu Jun 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.44-0
- fix job actions cancel and abort to call update_status()

* Wed Jun 16 2010 Bill Peck <bpeck@redhat.com> - 0.5.43-2
- update BeakerWorkflow to support --method and --kernel_options

* Wed Jun 16 2010 Bill Peck <bpeck@redhat.com> - 0.5.43-1
- require a valid user for xmlrpc job.upload()

* Tue Jun 15 2010 Bill Peck <bpeck@redhat.com> - 0.5.43-0
- bz581860	Listing of possible families
- bz589904 	tests which crashing the system will timeout the watchdog
- bz601220 	extendtesttime.sh does not work
- bz601485 	bkr --convert should convert CPUNAME to cpu_codename
- bz601763 	When trying to reserve a machine I get 500 Internal error
- bz602214 	--prettyxml option to bkr job-results doesn't work
- bz602907 	https://beaker.engineering.redhat.com/reserve_system defects
- bz602915 	Error with "Pick System" from Distro page 
- bz600098   	strip ansi chars from console.log so browsers show it as text/plain.

* Tue Jun 15 2010 Bill Peck <bpeck@redhat.com> - 0.5.42-4
- changed update_status() to not get into recursive loops
* Mon Jun 14 2010 Bill Peck <bpeck@redhat.com> - 0.5.42-3
- replace allow_limit_override=True with max_limit=None
* Tue Jun 08 2010 Bill Peck <bpeck@redhat.com> - 0.5.42-1
- bz570186 Hopefully fix: Ability to set system owner to a group or individual
- bz589904 tests which crashing the system will timeout the watchdog
- bz591384 getenv("TERM") returns NULL
- bz599086 improve configfile handling
- bz600353 Limiting architectures (releases) in Beaker 
* Mon Jun 07 2010 Bill Peck <bpeck@redhat.com> - 0.5.41-3
- added push and legacypush to proxy
* Tue Jun 01 2010 Bill Peck <bpeck@redhat.com> - 0.5.41-1
- minor update for bz598320
* Tue Jun 01 2010 Bill Peck <bpeck@redhat.com> - 0.5.41-0
- bz501511,RFE: Use STABLE trees by default
- bz582295,No Watchdog page anymore?
- bz583014,RFE] provide single_package.py replacement with same CLI interface
- bz584592,Inventory not UTF safe?
- bz591992,Job Status page: typo: ""Finsihed""
- bz594714,Beaker] [Job Matrix Report] Test column out of order leads to confusion
- bz596802,RFE] split bkr job-watch
- bz597155,variant option of workflow-simple doesn't work
- bz598320,show failed results' shows passed results also

* Tue May 25 2010 Bill Peck <bpeck@redhat.com> - 0.5.40-0
- minor fixes in command line workflow.
- minor fixes in command line task list.
- added new command distro-verify to help admins.
- 592978 "Change Job detail page to use AJAX for showing results"
- 570186 "[Beaker] RFE: Ability to set system owner to a group or individual"
- 541290 "[Beaker] RFE: Consistent use of the terminology."
- 580090 "Beaker doesn't take into account boot command line parameters"
- 594746 "[Beaker] [Execute Tasks] View does not report sub test results."
- 559337 "[Beaker] RFE: executed test report"
- 584586 "Importing labinfo results in 500 ISE"
- 584587 "Importing excludes doesn't work"
- 591147 "strange listing of systems with a particular devices"
- 591401 "RFE: User style searches for other admin pages."
- 594038 "Increase proper error handling"
* Mon May 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.39-0
- fix job_matrix report to show virt recipes as well.
* Mon May 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.38-1
- added --pid-file to beakerd startup. make sure only one beakerd is running at a time.
* Mon May 17 2010 Bill Peck <bpeck@redhat.com> - 0.5.38-0
- upaded proxy to only re-authenticate every 60 seconds.
- fixed beakerd to not look at systems not in Working state.
* Wed May 12 2010 Bill Peck <bpeck@redhat.com> - 0.5.37-0
- fixed proxy to fork properly
* Tue May 11 2010 Bill Peck <bpeck@redhat.com> - 0.5.36-0
- merged bz589723 - fix spelling mistakes
- merged bz589843 - cannot select systems in reserve workflow
- merged bz590665 - link to systems owner by a particular group gives internal error
- merged bz589857 - Distro search dies on 'Breed' search
* Mon May 10 2010 Bill Peck <bpeck@redhat.com> - 0.5.35-1
- Change default to /bkr
* Mon May 10 2010 Bill Peck <bpeck@redhat.com> - 0.5.35-0
- Fix beakerd to not do process_routine until all recipes are in state processed.
- possible fix for favicon.ico not being found.
* Fri May 07 2010 Bill Peck <bpeck@redhat.com> - 0.5.34-1
- fix syntax errors in beakerd
* Fri May 07 2010 Bill Peck <bpeck@redhat.com> - 0.5.34-0
- possible fix for same identity key exists in this session (beakerd)
- also fix it so scheduled_recipes routine always runs after queued_recipes
* Thu May 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.33-2
- pushed remote cobbler method to a ten minute timeout.  some power options take this long.
* Thu May 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.33-1
- added additional debug code to beakerd.
- default guest recipes to non virt distro, ask for it if you want virt.
* Thu May 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.33-0
- Remove --cost from rhel5 kickstart templates.  rhel5 doesn't support --cost.
* Wed May 05 2010 Bill Peck <bpeck@redhat.com> - 0.5.32-2
- fix workflow-simple to handle taskparam correctly and task types/packages
* Wed May 05 2010 Bill Peck <bpeck@redhat.com> - 0.5.32-1
- fix BeakerJob classes to add tasks to the correct node.
* Wed May 05 2010 Bill Peck <bpeck@redhat.com> - 0.5.32-0
- New beaker-client command workflow-simple
- minor fix to tasks/filter to support new workflow
* Wed Apr 28 2010 Bill Peck <bpeck@redhat.com> - 0.5.31-3
- only release_system if there is an active watchdog.
* Wed Apr 28 2010 Bill Peck <bpeck@redhat.com> - 0.5.31-2
- release_system should now catch tracebacks from failed cobbler attempts.
* Wed Apr 28 2010 Bill Peck <bpeck@redhat.com> - 0.5.31-1
- merged bz586163 - fixes job matrix report
* Wed Apr 28 2010 Bill Peck <bpeck@redhat.com> - 0.5.31-0
- added both provision methods to distro link
* Tue Apr 27 2010 Bill Peck <bpeck@redhat.com> - 0.5.30-0
- remove uneeded @identity on /distros/ 
* Mon Apr 26 2010 Bill Peck <bpeck@redhat.com> - 0.5.29-2
- switch show/hide links to buttons.
- hide logs by default
- show clone link for all jobs.
* Mon Apr 26 2010 Bill Peck <bpeck@redhat.com> - 0.5.29-1
- really fix package tag issues
* Mon Apr 26 2010 Bill Peck <bpeck@redhat.com> - 0.5.29-0
- fix package tag issues
* Sat Apr 24 2010 Bill Peck <bpeck@redhat.com> - 0.5.28-0
- compress task results by default, links for showall and showfail if failures
  state it remembered via a cookie.
* Fri Apr 23 2010 Bill Peck <bpeck@redhat.com> - 0.5.27-1
- fixed bad merge
* Fri Apr 23 2010 Bill Peck <bpeck@redhat.com> - 0.5.27-0
- bz583535 - RFE Provision from distro page
- bz582879 - Show all - bug in tasks library
- bz582186 - Searches should default to Contains
- bz581684 - Remove Tag page for Distros, distro page can now search on tags
- bz581502 - Sort distro family list
- bz567788 - search should show number of items returned
- update rhts_partitions snippet to allow ondisk specification
- update kickstarts to support firewall variable
- bz557116 - Show/search systems owned by groups
- bz582729 - Fixed html title to show job/recipe etc.. id on each page
- includes pub docs
* Tue Apr 20 2010 Bill Peck <bpeck@redhat.com> - 0.5.26-0
- Example cleanup in rhts_partitions snippet
- Fixed osversion.trigger not to process distros without ks_meta['tree']
- moved mod_wsgi socket location to /var/run to make fedora happy
- replaced Unicode() with UnicodeText() to make fedora happy
- add <packages><package name=""/></packages> tags so cloning works for custom_packages.
- loosen error checking on root name spaces for new tasks.
* Thu Apr 15 2010 Bill Peck <bpeck@redhat.com> - 0.5.25-0
- remove mod_python requirement from lab-controller
- Add X.log monitoring to anamon
* Wed Apr 14 2010 Bill Peck <bpeck@redhat.com> - 0.5.24-0
- added missing installPackage tag processing.
* Tue Apr 13 2010 Bill Peck <bpeck@redhat.com> - 0.5.23-2
- fixed install_start to push guest watchdog entries out as well.
* Tue Apr 13 2010 Bill Peck <bpeck@redhat.com> - 0.5.23-1
- Merge remote branch 'origin/bz541281' No sorting, filtering, or pagination settings on Accounts list
- Merge remote branch 'origin/bz580091' quick links on Job/Recipe pages for "Running", "Queued"
* Tue Apr 13 2010 Bill Peck <bpeck@redhat.com> - 0.5.23-0
- fix firewall syntax for mutliple ports
* Mon Apr 12 2010 Bill Peck <bpeck@redhat.com> - 0.5.22-2
- add system specific kickstart snippets
- Merge remote branch 'origin/bz578420'
- Merge remote branch 'origin/master_variables'
- Merge remote branch 'origin/job_submit_nowait'
* Mon Apr 12 2010 Bill Peck <bpeck@redhat.com> - 0.5.22-1
- Opened port 12432 for beah multi-host by default.
* Mon Apr 12 2010 Bill Peck <bpeck@redhat.com> - 0.5.22-0
- Added recipeset_stop to proxy method.
* Sat Apr 10 2010 Bill Peck <bpeck@redhat.com> - 0.5.21-1
- cherry-picked rcm addRepo code from 0.4.x
* Sat Apr 10 2010 Bill Peck <bpeck@redhat.com> - 0.5.21-0
- fixed beakerd filtering on Status, actually is SystemStatus.
* Fri Apr 09 2010 Bill Peck <bpeck@redhat.com> - 0.5.20-0
- prepend log dir with year of start_time.
* Thu Apr 08 2010 Bill Peck <bpeck@redhat.com> - 0.5.19-1
- fixed scheduler to honor system status.
* Thu Apr 08 2010 Bill Peck <bpeck@redhat.com> - 0.5.19-0
- Merge remote branch 'origin/bz576327'
- Merge remote branch 'origin/bz579972'
- Merge remote branch 'origin/bz578383'
- Fixed --convert to handle <partition> tags in legacy xml
* Wed Apr 07 2010 Bill Peck <bpeck@redhat.com> - 0.5.18-3
- BZ #578548 - fix provided by gozen
- fixed hostRequires and distroRequires parsing to not choke on empty <and/> or <or/> tags
- display time left in duration column if watchdog exists
* Tue Apr 06 2010 Bill Peck <bpeck@redhat.com> - 0.5.17-2
- fixed bz 570986, "TypeError: string indices must be integers" in expire_distros
- fixed task_stop(cancel or abort) returning None.
- fixed child.filter() to not die on unrecognized tags.
* Mon Apr 05 2010 Bill Peck <bpeck@redhat.com> - 0.5.16-2
- make sure old task rpm exists before trying to remove it.
- overwrite repos, don't append in rhts_post snippet.
* Thu Apr 01 2010 Bill Peck <bpeck@redhat.com> - 0.5.15-8
- fix apache conf for beaker-server
- pass repos to cobbler, separate harness_repos from custom_repos
- allow ks_meta to be passed in from recipe
* Wed Mar 31 2010 Bill Peck <bpeck@redhat.com> - 0.5.15-1
- move harness repos to server from lab-controller.
* Wed Mar 31 2010 Bill Peck <bpeck@redhat.com> - 0.5.14-0
- update rhts-post snippet to only enable our repos.
* Tue Mar 30 2010 Bill Peck <bpeck@redhat.com> - 0.5.13-1
- removed uneeded task_list code
- default task result to pass when no result recorded, this is for css display.
- display log summary when task.path == /
* Mon Mar 29 2010 Bill Peck <bpeck@redhat.com> - 0.5.12-1
- merged bz574179, arch and distro search in tasks.
- added stdin support for bkr job-submit
- minor spec file changes for fedora package review.
- added xmlrpc method to tasks for getting list of all tasks
- added command module to list tasks
* Fri Mar 26 2010 Bill Peck <bpeck@redhat.com> - 0.5.11-0
- fix status_watchdog to return correct seconds if remaining time is over a day.
* Thu Mar 25 2010 Bill Peck <bpeck@redhat.com> - 0.5.10-0
- Added missing code to deal with priorities.
- Added missing code to order available systems by Owner,Group, then shared.
- fixed extend_watchdog to return status_watchdog()
- added status_watchdog method to return the number of seconds remaining on watchdog.
- added missing user variable for system sorting.
* Wed Mar 24 2010 Bill Peck <bpeck@redhat.com> - 0.5.8-1
- removed -lib subpackage. beakerlib is now its own project.
- fixed extend_watchdog to not return None.
* Wed Mar 24 2010 Bill Peck <bpeck@redhat.com> - 0.5.6-2
- merged rmancy fix for bz576446 - added MyJobs/MyRecipe links to menu.
- moved My menus to Login area.
* Tue Mar 23 2010 Bill Peck <bpeck@redhat.com> - 0.5.5-0
- merged rmancy fix for bz574178 - added recipe search.
* Tue Mar 23 2010 Bill Peck <bpeck@redhat.com> - 0.5.4-0
- merged rmancy fix for bz576420 - fixes task search
* Tue Mar 23 2010 Bill Peck <bpeck@redhat.com> - 0.5.3-0
- merged rmancy fix for bz574176 - searching in jobs 
- merged mcsontos fix for bz576128 - add help for beaker-client subcommands
* Thu Mar 18 2010 Bill Peck <bpeck@redhat.com> - 0.5.2-0
- Merged Scheduler into master, renamed site-packages/beaker to site-packages/bkr
* Thu Mar 04 2010 Bill Peck <bpeck@redhat.com> - 0.4.89-0
- update osversion.trigger to update pushed data before calling addDistro.sh
* Wed Mar 03 2010 Bill Peck <bpeck@redhat.com> - 0.4.88-0
- update osversion.trigger to ignore xen variants when calling addDistro.sh
* Wed Mar 03 2010 Bill Peck <bpeck@redhat.com> - 0.4.87-0
- fixed osversion.trigger, FAMILYUPDATE may not exist for some distros.
* Tue Mar 02 2010 Bill Peck <bpeck@redhat.com> - 0.4.86-1
- fixed osversion.trigger, Distro -> distro.
- extend visit timeout to 6 hours by default.
- really include System/Location in search bar.
* Wed Feb 24 2010 Bill Peck <bpeck@redhat.com> - 0.4.85-2
- Added @x11 and @basic-desktop to rhel6 kickstarts
* Fri Feb 19 2010 Raymond Mancy <rmancy@redhat.com> - 0.4.85-1
- refactored system search
- cast partition size to int() before multiplying. 
* Wed Feb 17 2010 Bill Peck <bpeck@redhat.com> - 0.4.84-1
- update osversion.trigger to only process newly imported distros
- add robustness to rhts_partitions snippet.
- rmancy merged history search.
* Mon Feb 15 2010 Bill Peck <bpeck@redhat.com> - 0.4.83-0
- Remove auth from rhel6 kickstart, default is sane.
- Includes rmancy's update, added cpu_model_name to search options.
- escape variables in cheetah snippets.
* Wed Feb 03 2010 Bill Peck <bpeck@redhat.com> - 0.4.82-3
- Don't expire nightlies in one week, leave it up to the filesystem
- fix bz#554852 don't remove any distros if all are missing
- Process KickPart directive from legacy rhts if passed in.
- Update rhts_partitions snippet to support fstype
- run addDistro.sh with variant specified in .treeinfo if available
- install options should override base options
* Tue Feb 02 2010 Bill Peck <bpeck@redhat.com> - 0.4.81-2
- Fix bz#560823 for rhel3 systems not checking in to rhts properly
- Fix ISE 500 when looking up an invalid profile on cobbler
- Fix for rt#58689 when importing anything but an nfs distro we get the location 
  of the repos wrong.
- Fix bz#555551 - missing location for search and custom columns
- Fix bz#559656 - unable to handle commented %%packages in kickstart
- Merged AccountClosure code.
* Tue Jan 26 2010 Bill Peck <bpeck@redhat.com> - 0.4.80-0
- added support for variants being read from .treeinfo
* Mon Jan 25 2010 Bill Peck <bpeck@redhat.com> - 0.4.79-1
- add missing admin decorators to user methods
* Fri Jan 22 2010 Bill Peck <bpeck@redhat.com> - 0.4.79-0
- rename table key to key_, key is a reserved word.
- shorten key_name value to varchar(50) to support mysql Unique column limitation.
* Wed Jan 20 2010 Bill Peck <bpeck@redhat.com> - 0.4.78-0
- Remove redundant arch aliases
* Wed Jan 13 2010 Bill Peck <bpeck@redhat.com> - 0.4.77-0
- fix ISE 500 when adding new system
* Tue Jan 12 2010 Bill Peck <bpeck@redhat.com> - 0.4.76-1
- fix for cookies not being set.
* Tue Jan 12 2010 Bill Peck <bpeck@redhat.com> - 0.4.76-0
- merged bz554775 - added missing search columns and changed the order of Family/Model.
* Mon Jan 11 2010 Bill Peck <bpeck@redhat.com> - 0.4.76-0
- merged bz544347 - add condition field when system status set to broken or removed.
- merged ticket51 - custom columns.
- merged bz553421 - fixed requesting a system with arch=i386 and arch=x86_64 would fail.
* Fri Jan 08 2010 Bill Peck <bpeck@redhat.com> - 0.4.76-0
- Fixed regression, remove pxe entries when returning a system.
* Thu Jan 07 2010 Bill Peck <bpeck@redhat.com> - 0.4.76-0
- merged bz537414 - show version on beaker pages and have a link for reporting bugs.
* Tue Jan 05 2010 Bill Peck <bpeck@redhat.com> - 0.4.75-1
- Server/Client/LabController require beaker.
* Tue Jan 05 2010 Bill Peck <bpeck@redhat.com> - 0.4.74-0
- Merged Raymond's bz549912
- updated spec file to include branch name and timestamp
* Tue Dec 22 2009 Bill Peck <bpeck@redhat.com> - 0.4.70-0
- another fix to the release_action code. send proper action methods
  to cobbler, Off->off On->on.
* Thu Dec 17 2009 Bill Peck <bpeck@redhat.com> - 0.4.69-0
- small fix for release action, default to power off.
* Fri Dec 11 2009 Bill Peck <bpeck@redhat.com> - 0.4.68-0
- osversion now knows what arches are expected for that update.
  This allows us to only tag distros as STABLE if all arches are imported and tagged as INSTALLS
- update distro-list command to show the distro name, suitable for feeding into workflows.
* Wed Dec 09 2009 Bill Peck <bpeck@redhat.com> - 0.4.67-0
- Raymonds fix for is_not in arch search
- additional fixes from Raymond
- fix for beaker-init to create ReleaseAction Table
* Sun Dec 06 2009 Bill Peck <bpeck@redhat.com> - 0.4.65-0
- New ReleaseAction code, allows systems to stay on or
  reprovision at time of return.
* Tue Dec 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.64-0
- Fix ISE in simplesearch
- added PATH=/usr/bin:$PATH to rhel3 kickstart
* Fri Nov 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.63-0
- merged Raymond's Key/Value search ability
* Fri Nov 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.62-1
- Fixes for searching drivers
- Random selection when more than one host available.
* Tue Nov 17 2009 Bill Peck <bpeck@redhat.com> - 0.4.61-0
- Fixes for searching on cpuflags
- new manual kickstart keyword allows interactive installs
* Wed Oct 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.57-0
- New search implemented by Raymond Mancy
- don't try and power off machines that were temporarily reserved by legacy rhts
- view groups for non admin users
* Fri Oct 16 2009 Bill Peck <bpeck@redhat.com> - 0.4.53-0
- fix allows custom kickstarts to still append packages
* Tue Oct 06 2009 Bill Peck <bpeck@redhat.com> - 0.4.52-0
- pass !key along to cobbler for further processing.
* Mon Oct 05 2009 Bill Peck <bpeck@redhat.com> - 0.4.51-0
- fix for reserve report, not all records have a Reserved action.
* Thu Oct 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.50-0
- Fixed system exclude to work properly from Distro.systems()
  previously excluding one arch would exclude all.
- added first report. reserve, shows length of currently reserved systems
- updated reserve report to honor NDA/secret settings.
* Wed Sep 30 2009 Petr Muller <pmuller@redhat.com> - 0.4.46-0
- backported few beakerlib fixes from the development branch
* Wed Sep 29 2009 Bill Peck <bpeck@redhat.com> - 0.4.45-0
- updated rhts-checkin to report anaconda logs to legacy rhts.
* Tue Sep 15 2009 Bill Peck <bpeck@redhat.com> - 0.4.44-0
- fixed wrong default language for Fedora kickstarts
- attempted to make broken search a little better.
* Thu Sep 10 2009 Bill Peck <bpeck@redhat.com> - 0.4.43-0
- added RHEL6/F12 package groups for development
* Thu Sep 03 2009 Bill Peck <bpeck@redhat.com> - 0.4.42-0
- fixed saving tag Activity on Distro.
* Thu Aug 27 2009 Bill Peck <bpeck@redhat.com> - 0.4.41-0
- use action_release() in controllers
* Thu Aug 27 2009 Bill Peck <bpeck@redhat.com> - 0.4.40-0
- option to not wait for power commands if talking to cobbler 1.7 or newer
* Tue Aug 25 2009 Bill Peck <bpeck@redhat.com> - 0.4.39-7
- re-worked remote calls to cobbler to be in their own sub-class.
  This was needed to support the latest version of cobbler.
- added not_anonymous tags around distro tagi add/remove methods.
* Fri Aug 21 2009 Petr Muller <pmuller@redhat.com> - 0.4.39-0
- cherry picked fixes from master branch for beakerlib:
- various doc fixes
- tweaked phase reporting 
- new options & functionality for rlRun
- enabling manual use of journal comparator
- new rlPass and rlFail functions
- new rlSendFile function
- plugin mechanism
- xml character breakage fix
* Thu Aug 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.38-0
- Allow skipx in kickstarts to be passed in from metadata.
- Added xmlrpc method for editing distro Update.
* Wed Aug 12 2009 Bill Peck <bpeck@redhat.com> - 0.4.37-0
- Escape $ in custom kickstarts sent to cobbler
* Tue Aug 11 2009 Bill Peck <bpeck@redhat.com> - 0.4.36-0
- create subprofile
* Mon Aug 10 2009 Bill Peck <bpeck@redhat.com> - 0.4.34-0
- Change how custom kickstarts are handled. Don't copy
  cobbler profiles anymore, just use system profile and set
  parent if needed.
* Fri Aug 07 2009 Bill Peck <bpeck@redhat.com> - 0.4.33-0
- Allow the owner of a system to force a loan return.
* Wed Aug 05 2009 Bill Peck <bpeck@redhat.com> - 0.4.32-0
- Require users to be logged in to do actions and saves.
  This forces an automatic relogin if using kerberos.
* Tue Aug 04 2009 Bill Peck <bpeck@redhat.com> - 0.4.31-0
- fixed remove_distro call in expire distros
* Mon Aug 03 2009 Bill Peck <bpeck@redhat.com> - 0.4.30-0
- Updated osversion.trigger to not traceback when encountering an 
  unknown compressor.
* Tue Jul 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.29-0
- Changes cobbler scripts to do everything through xmlrpc.
  cobbler gets confused otherwiese.
* Fri Jul 24 2009 Bill Peck <bpeck@redhat.com> - 0.4.28-0
- Fixed string_to_hash to not barf on extra spaces
* Mon Jul 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.27-0
- Expanded user_name field to 255 chars.
* Mon Jul 20 2009 Bill Peck <bpeck@redhat.com> - 0.4.26-0
- Enable ntp in cobbler snippets
* Fri Jul 17 2009 Bill Peck <bpeck@redhat.com> - 0.4.25-0
- Fixed system arch filtering to be unicode not int.
* Thu Jul 16 2009 Bill Peck <bpeck@redhat.com> - 0.4.24-0
- Allow systems to query on arch even though we are already starting
  from a distro.  This allows you to ask for systems that are not x86_64
  for example.
- Don't fail if we can't power off a system when returning it.
- Use correct username when returning a system to the pool.
- Remove --resolvedeps from RHEL6 kickstart file.
* Tue Jul 14 2009 Bill Peck <bpeck@redhat.com> - 0.4.22-0
- Fix distro_method value to be unicode instead of boolean.
* Mon Jul 13 2009 Bill Peck <bpeck@redhat.com> - 0.4.21-0
- Allow legacy RHTS to ask for distros based on install method
* Tue Jul 07 2009 Bill Peck <bpeck@redhat.com> - 0.4.20-0
- Include Workstation key for RedHatEnterpriseLinuxClient5
* Mon Jul 06 2009 Bill Peck <bpeck@redhat.com> - 0.4.19-0
- Don't populate runtest_url in ks_meta if its not defined.
* Wed Jul 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.18-2
- Use RUNTEST_URL from rhts if passed.
- Include Fedoradevelopment.ks for rawhide
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.17-0
- Call the correct method for _tag
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.16-0
- update login_krbv method for newer kobo package
* Tue Jun 30 2009 Bill Peck <bpeck@redhat.com> - 0.4.15-0
- Call addDistros.sh from osversion.trigger if it exists.
* Mon Jun 29 2009 Bill Peck <bpeck@redhat.com> - 0.4.14-0
- Allow searching by treepath for command line client
- return distro name for legacy rhts.
* Mon Jun 22 2009 Bill Peck <bpeck@redhat.com> - 0.4.13-0
- Fixed osversion.trigger to work with methods other than nfs
* Fri Jun 19 2009 Bill Peck <bpeck@redhat.com> - 0.4.12-0
- Raise BeakerExceptions if we run into trouble
* Thu Jun 18 2009 Bill Peck <bpeck@redhat.com> - 0.4.11-0
- added install_name to distro pick method
- fixed 500 error when non-admin adds a new system with shared set.
* Fri Jun 12 2009 Bill Peck <bpeck@redhat.com> - 0.4.9-1
- releng fixed the name of rhel6 to RedHatEnterpriseLinux6 in .treeinfo
* Wed Jun 10 2009 Bill Peck <bpeck@redhat.com> - 0.4.9
- Added simple json method for tagging distros as Installable.
- Added RHEL6 kickstart file.
* Wed Jun 03 2009 Bill Peck <bpeck@redhat.com> - 0.4.8
- Catch xmlrpc errors from cobbler and record/display them
* Mon Jun 01 2009 Bill Peck <bpeck@redhat.com> - 0.4.7
- added distros list,tag,untag to beaker-client
- fixed some minor issues with the xmlrpc interface.
* Thu May 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.6
- Clear systems console log via xmlrpc
* Thu May 28 2009 Bill Peck <bpeck@redhat.com> - 0.4.5
- free and available views will only show working systems now.
* Tue May 26 2009 Bill Peck <bpeck@redhat.com> - 0.4.4
- Fixed missing power_id from CSV import/export
- Use $default_password_crypted from /etc/cobbler/settings unless $password 
  is set.
* Fri May 22 2009 Bill Peck <bpeck@redhat.com> - 0.4.2
- Added in beakerlib sub package
- Fixed tempfile close in osversion.trigger
* Thu May 21 2009 Bill Peck <bpeck@redhat.com> - 0.4-3
- fix power import
* Tue May 19 2009 Bill Peck <bpeck@redhat.com> - 0.4-1
- Major reworking of directory layout.
* Tue May 12 2009 Bill Peck <bpeck@redhat.com> - 0.3-1
- First stab at client interface
