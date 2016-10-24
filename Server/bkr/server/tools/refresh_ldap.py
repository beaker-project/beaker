
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

__description__ = 'Refreshes group membership from LDAP'

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['TurboGears']

import sys
import logging
import optparse
import ldap
from turbogears import config
from bkr.common import __version__
from bkr.log import log_to_stream
from bkr.server.util import load_config_or_exit
from bkr.server.model import session, Group, GroupMembershipType

def refresh_ldap():
    with session.begin():
        # reuse a single LDAP connection for efficiency
        ldapcon = ldap.initialize(config.get('identity.soldapprovider.uri'))
        for group in Group.query.filter(Group.membership_type == GroupMembershipType.ldap):
            group.refresh_ldap_members(ldapcon)

def main():
    parser = optparse.OptionParser('usage: %prog [options]',
            description=__description__,
            version=__version__)
    parser.add_option('-c', '--config', metavar='FILENAME',
            help='Read configuration from FILENAME')
    parser.add_option('--debug', action='store_true',
            help='Print debugging messages to stderr')
    parser.set_defaults(debug=False)
    options, args = parser.parse_args()
    load_config_or_exit(options.config)
    log_to_stream(sys.stderr, level=logging.DEBUG if options.debug else logging.WARNING)

    # beaker-server ships a cron job to run this command, so exit silently 
    # and quickly if LDAP is not actually enabled.
    if not config.get('identity.ldap.enabled', False):
        return 0

    refresh_ldap()
    return 0

if __name__ == '__main__':
    sys.exit(main())
