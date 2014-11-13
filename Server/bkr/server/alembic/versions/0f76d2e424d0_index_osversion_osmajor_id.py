# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Index osversion.osmajor_id

Revision ID: 0f76d2e424d0
Revises: 2c0f1c0a668b
Create Date: 2014-10-10 12:38:16.945789

"""

# revision identifiers, used by Alembic.
revision = '0f76d2e424d0'
down_revision = '2c0f1c0a668b'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('osversion')
    if not any(index['column_names'] == ['osmajor_id'] for index in indexes):
        op.create_index('ix_osversion_osmajor_id', 'osversion', ['osmajor_id'])

def downgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('osversion')
    if any(index['name'] == 'ix_osversion_osmajor_id' for index in indexes):
        op.drop_index('ix_osversion_osmajor_id', 'osversion')
