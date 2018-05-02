# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Alembic revision 3ba776df4c76 was supposed to INSERT rows into the
'installation' table for recipes that were not yet provisioned at the time when
Beaker was upgraded to 25. It originally had a bug where it was ignoring
recipes in the 'Scheduled' state. That migration is fixed now, but we also
repeat the same INSERT statement here, for Beaker sites which were already
upgraded using the buggy version of the Alembic migration.
"""

import logging


logger = logging.getLogger(__name__)


def migrate_one_batch(engine):
    # This migration turned out to be not effective. There were more jobs in
    # different states affected than just a forgotten 'Scheduled' recipe state.
    # See insert-installation-row-for-recipes-before-25-take-2.py for the
    # actual online migration which fixes this.
    return True
