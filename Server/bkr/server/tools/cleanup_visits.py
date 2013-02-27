#!/usr/bin/env python
# Beaker
#
# Copyright (C) 2010 dcallagh@redhat.com
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

# -*- coding: utf-8 -*-

__version__ = '0.1'
__description__ = 'Cleans up stale records from the Beaker visit table'
# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
import datetime
from optparse import OptionParser

# http://docs.turbogears.org/1.0/UsingVisitFramework#housekeeping
def cleanup_visits(keep_days):
    from turbogears.database import session
    from bkr.server.model import metadata
    from sqlalchemy import not_, select
    session.begin()
    try:
        visit = metadata.tables['visit']
        visit_identity = metadata.tables['visit_identity']
        session.execute(visit.delete(visit.c.expiry <
                (datetime.datetime.now() - datetime.timedelta(days=keep_days))))
        # XXX we could use CASCADE DELETE for this
        session.execute(visit_identity.delete(
                not_(visit_identity.c.visit_key.in_(select([visit.c.visit_key])))))
        session.commit()
    except:
        session.rollback()
        raise

def main():
    parser = OptionParser('usage: %prog [options]',
            description=__description__, version=__version__)
    parser.add_option('-c', '--config', metavar='FILENAME',
            help='Read configuration from FILENAME')
    parser.add_option('-k', '--keep', metavar='DAYS',
            help='Keep records which expired less than DAYS ago [default: %default]')
    parser.set_defaults(keep=7)
    options, args = parser.parse_args()

    from bkr.server.util import load_config, log_to_stream
    load_config(options.config)
    log_to_stream(sys.stderr)

    cleanup_visits(options.keep)

if __name__ == '__main__':
    main()
