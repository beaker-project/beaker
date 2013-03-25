#!/bin/sh
set -e

# update Beaker config to match what the tests are expecting
sed --regexp-extended --in-place=-orig --copy -e '
    s@^#?tg.url_domain.*$@tg.url_domain = "localhost"@
    s@^#?mail.on.*$@mail.on = True@
    s@^#?mail.smtp.server.*$@mail.smtp.server = "127.0.0.1:19999"@
    s@^#?beaker.reliable_distro_tag.*$@beaker.reliable_distro_tag = "RELEASED"@
    s@^#?beaker.motd.*$@beaker.motd = "/usr/lib/python2.6/site-packages/bkr/inttest/server/motd.xml"@
    s@^#?beaker.max_running_commands .*$@beaker.max_running_commands = 10@
    s@^#?beaker.kernel_options .*$@beaker.kernel_options = "noverifyssl"@
    ' /etc/beaker/server.cfg

# reduce number of Apache worker processes, to save a bit of memory
sed --regexp-extended --in-place=-orig --copy -e '
    /^WSGIDaemonProcess/ s@processes=[0-9]+@processes=2@
    ' /etc/httpd/conf.d/beaker-server.conf
