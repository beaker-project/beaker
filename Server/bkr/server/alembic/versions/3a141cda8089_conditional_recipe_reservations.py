# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Conditional recipe reservations

Revision ID: 3a141cda8089
Revises: 468779d8e8
Create Date: 2016-10-12 16:05:55.939714
"""

# revision identifiers, used by Alembic.
revision = '3a141cda8089'
down_revision = '468779d8e8'

from alembic import op
from sqlalchemy import Column, Enum

def upgrade():
    when_enum_type = Enum(u'always', u'onwarn', u'onfail', u'onabort')
    # Once with server_default to populate existing rows...
    op.add_column('recipe_reservation', Column('when', when_enum_type,
            nullable=False, server_default=u'always'))
    # Then take the server_default back out, to match the model definition.
    op.alter_column('recipe_reservation', 'when',
            existing_type=when_enum_type, server_default=None)

def downgrade():
    op.drop_column('recipe_reservation', 'when')
