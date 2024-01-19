
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Helper to allow beaker-proxy to clear netboot files synchronously
# even though it isn't running as root

# Executing this via sudo means we can avoid adding a separate local
# service API to beaker-provision (with associated access control
# mechanisms, etc).

# Required sudoers entry to allow beaker-proxy access:
#
#     apache ALL=(ALL) NOPASSWD:  /usr/bin/beaker-clear-netboot
#
# Lab controller RPM installs it as: /etc/sudoers.d/beaker_proxy_clear_netboot


import sys
from optparse import OptionParser

from bkr.labcontroller import netboot


def main():
    usage = "usage: %prog FQDN"
    description = "Clears the Beaker TFTP netboot files for the given FQDN"
    parser = OptionParser(usage=usage, description=description)
    (opts, args) = parser.parse_args()
    if len(args) != 1:
        sys.stderr.write("Must specify exactly 1 FQDN to be cleared\n")
        sys.exit(1)

    # Our sanity check on the untrusted argument is that the relevant
    # image directory must exist in the TFTP directory or we won't
    # even try to delete anything
    fqdn = args[0]
    if netboot.have_images(fqdn):
        netboot.clear_all(fqdn)


if __name__ == '__main__':
    main()
