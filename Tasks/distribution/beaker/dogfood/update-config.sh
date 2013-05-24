#!/bin/sh
set -e

# Updates the Beaker config to match what the tests are expecting.

if [ -e /etc/beaker/server.cfg ] ; then
    sed --regexp-extended --in-place=-orig --copy -e '
        /^#?tg\.url_domain/c                tg.url_domain = "localhost"
        /^#?mail\.on/c                      mail.on = True
        /^#?mail\.smtp\.server/c            mail.smtp.server = "127.0.0.1:19999"
        /^#?beaker\.reliable_distro_tag/c   beaker.reliable_distro_tag = "RELEASED"
        /^#?beaker\.motd/c                  beaker.motd = "/usr/lib/python2.6/site-packages/bkr/inttest/server/motd.xml"
        /^#?beaker\.max_running_commands /c beaker.max_running_commands = 10
        /^#?beaker\.kernel_options /c       beaker.kernel_options = "noverifyssl"
        /^#?identity\.ldap\.enabled/c       identity.ldap.enabled = True
        /^#?identity\.soldapprovider\.uri/c identity.soldapprovider.uri = "ldap://localhost:3899/"
        /^#?identity\.soldapprovider\.basedn/c identity.soldapprovider.basedn = "dc=example,dc=invalid"
        /^#?identity\.soldapprovider\.autocreate/c identity.soldapprovider.autocreate = True
        ' /etc/beaker/server.cfg
fi

if [ -e /etc/httpd/conf.d/beaker-server.conf ] ; then
    # reduce number of Apache worker processes, to save a bit of memory
    sed --regexp-extended --in-place=-orig --copy -e '
        /^WSGIDaemonProcess/ s@processes=[0-9]+@processes=2@
        ' /etc/httpd/conf.d/beaker-server.conf
    service httpd reload
fi

if [ -e /etc/beaker/labcontroller.conf ] ; then
    sed --regexp-extended --in-place=-orig --copy -e '
        $a SLEEP_TIME = 5
        ' /etc/beaker/labcontroller.conf
    service beaker-proxy condrestart
    service beaker-provision condrestart
    service beaker-watchdog condrestart
    service beaker-transfer condrestart
fi
