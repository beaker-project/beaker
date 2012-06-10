#!/bin/sh
set -e

# update Beaker config to match what the tests are expecting
cp /etc/beaker/server.cfg /etc/beaker/server.cfg-orig
sed -r '
    s@^#?tg.url_domain.*$@tg.url_domain = "localhost"@
    s@^#?mail.on.*$@mail.on = True@
    s@^#?mail.smtp.server.*$@mail.smtp.server = "127.0.0.1:19999"@
    s@^#?beaker.reliable_distro_tag.*$@beaker.reliable_distro_tag = "RELEASED"@
    s@^#?beaker.motd.*$@beaker.motd = "/usr/lib/python2.6/site-packages/bkr/inttest/server/motd.xml"@
    s@^#?beaker.kernel_options.*$@beaker.kernel_options = "noverifyssl"@
' </etc/beaker/server.cfg-orig >/etc/beaker/server.cfg
