# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add missing unique constraint on beaker_tag

Revision ID: 01a7a1210068
Revises: 218cc5b1c361
Create Date: 2014-10-10 13:47:00.327503

"""

# revision identifiers, used by Alembic.
revision = '01a7a1210068'
down_revision = '218cc5b1c361'

from alembic import op
import sqlalchemy as sa

def upgrade():
    uniques = sa.inspect(op.get_bind()).get_unique_constraints('beaker_tag')
    if not any(unique['column_names'] == ['tag', 'type'] for unique in uniques):
        op.create_unique_constraint('tag', 'beaker_tag', ['tag', 'type'])

def downgrade():
    pass # no downgrade because we are fixing a mistake in an upgrade
