# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add index on tg_user.email_address

Revision ID: 50bc9c21974b
Revises: 3059fb224ff5
Create Date: 2014-10-07 15:59:13.917203

"""

# revision identifiers, used by Alembic.
revision = '50bc9c21974b'
down_revision = '3059fb224ff5'

from alembic import op
import sqlalchemy as sa

def upgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('tg_user')
    if not any(index['column_names'] == ['email_address'] for index in indexes):
        op.create_index('ix_tg_user_email_address', 'tg_user', ['email_address'])

def downgrade():
    indexes = sa.inspect(op.get_bind()).get_indexes('tg_user')
    if any(index['name'] == 'ix_tg_user_email_address' for index in indexes):
        op.drop_index('ix_tg_user_email_address', 'tg_user')
