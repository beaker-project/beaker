#!/usr/bin/env python

# Beaker
#
# Copyright (C) 2010 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import bkr
from bkr.server.model import System, User
from turbogears.database import session
from optparse import OptionParser
import sys
import logging

def delete_system(fqdn, dry_run=False):
    session.begin()
    try:
        admin = User.by_user_name(u'admin')
        system = System.by_fqdn(fqdn, admin)
        if system.recipes:
            raise ValueError('Cannot delete system %s with recipes' % fqdn)
        session.delete(system)
        session.flush()
        if dry_run:
            session.rollback()
        else:
            session.commit()
    finally:
        session.close()

def main():
    parser = OptionParser('usage: %prog [options] fqdn ...',
            description='Permanently deletes system records from Beaker.',
            version=bkr.__version__)
    parser.add_option('-c', '--config', metavar='FILENAME',
            help='Read configuration from FILENAME')
    parser.add_option('-v', '--verbose', action='store_true',
            help='Log SQL statements executed')
    parser.add_option('--dry-run', action='store_true',
            help='Execute deletions, but issue ROLLBACK instead of COMMIT')
    parser.set_defaults(verbose=False, dry_run=False)
    options, args = parser.parse_args()

    if len(args) < 1:
        parser.error('Specify at least one system to delete')

    from bkr.server.util import load_config, log_to_stream
    load_config(options.config)
    log_to_stream(sys.stderr)

    if options.verbose:
        logger = logging.getLogger('sqlalchemy.engine')
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler(sys.stderr))

    for fqdn in args:
        delete_system(fqdn.decode('ascii'), options.dry_run)

if __name__ == '__main__':
    main()

