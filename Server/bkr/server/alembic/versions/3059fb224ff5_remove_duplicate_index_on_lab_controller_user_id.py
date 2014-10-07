# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Remove duplicate index on lab_controller.user_id

Revision ID: 3059fb224ff5
Revises: 19b9071910f9
Create Date: 2014-10-07 15:48:59.596520

"""

# revision identifiers, used by Alembic.
revision = '3059fb224ff5'
down_revision = '19b9071910f9'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('lab_controller')
    if (any(index['name'] == 'user_id' for index in indexes) and
        any(index['name'] == 'uc_user_id' for index in indexes)):
        op.drop_index('user_id', 'lab_controller')

def downgrade():
    pass # no downgrade because we are fixing a mistake in an upgrade
