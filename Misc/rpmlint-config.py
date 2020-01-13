
from Config import addFilter

# It's true, our server-side man pages are deficient
addFilter(r'(beaker-server|beaker-lab-controller)\.noarch: W: no-manual-page-for-binary')

# Kid templates produce a .pyc without a corresponding .py when they are compiled
addFilter(r'python-bytecode-without-source /usr/lib/python.*/site-packages/bkr/server/templates/.*\.pyc')

# We ship the same logrotate config file for both server and lab-controller,
# so it's just called "beaker"
addFilter(r'incoherent-logrotate-file /etc/logrotate\.d/beaker')

# These are intentionally non-world-readable
addFilter(r'non-readable /etc/beaker/server\.cfg')
addFilter(r'non-readable /etc/sudoers\.d/beaker_proxy_clear_netboot')

# These are intentionally non-executable, they are executed on test systems instead
addFilter(r'non-executable-script /usr/share/bkr/lab-controller/(anamon|anamon\.init|anamon\.service)')

# This is intentionally not-executable, they are executed on test systems instead
addFilter(r'non-executable-script /usr/lib/python.*/site-packages/bkr/labcontroller/pxemenu-templates/ipxe-menu')

# This is just an rpmlint bug really - This should be executed by iPXE
addFilter(r'wrong-script-interpreter /usr/lib/python.*/site-packages/bkr/labcontroller/pxemenu-templates/ipxe-menu')

# On RHEL6 bash completions are indeed stored in /etc even though they are not
# config. Newer bash-completion moved this to /usr/lib and the problem goes
# away. So delete this when we're not targetting RHEL6 anymore.
addFilter(r'non-conffile-in-etc /etc/bash_completion\.d/bkr')

# RHEL6-only pid file stuff. Under systemd we should be neither owning, nor
# creating, nor using any of this stuff in /var/run.
addFilter(r'dir-or-file-in-var-run /var/run/(beaker|beaker-lab-controller)')

# This cron job is both executable and configuration intentionally,
# this might be violating some packaging guidelines... need to check.
addFilter(r'executable-marked-as-config-file /etc/cron\.hourly/beaker_expire_distros')

# Fake compose data uses empty hidden files to produce the directory structure
addFilter(r'(zero-length|hidden-file-or-dir) /usr/lib/python.*/site-packages/bkr/inttest/labcontroller/compose_layout/')

# Fake client config included with tests
addFilter(r'hidden-file-or-dir /usr/lib/python.*/site-packages/bkr/inttest/client/.beaker_client')

# We are guilty of using jargon from time to time
addFilter(r'spelling-error.* (netboot|distro|distros)')

# We know what we're doing
addFilter(r'dangerous-command-in-%post rm')
addFilter(r'dangerous-command-in-%preun rm')

# No %doc is okay for these as they depend on other subpackages
addFilter(r'(beaker-lab-controller-addDistro|beaker-integration-tests)\.noarch: W: no-documentation')

# RPMs built from git have no %changelog, the proper ones maintained from dist-git do though
addFilter(r'no-changelogname-tag')

# /dev/null always exists
addFilter(r'dangling-symlink .* /dev/null')

# Our initscripts are okay, rpmlint just can't understand the variable substitution
addFilter(r'incoherent-subsys .* \$prog')

# rpmlint is being a bit preachy (we really don't need or want reload)
addFilter(r'no-reload-entry /etc/init\.d/beakerd')

# We can call our services whatever we want
addFilter(r'incoherent-init-script-name beakerd')

# This is just an rpmlint bug really
addFilter(r'explicit-lib-dependency (libxml2-python|libxslt-python|python-passlib)')
