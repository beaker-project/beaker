# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""make kernel_options column nullable

Revision ID: 2441049ac32c
Revises: 2a56e56fbe26
Create Date: 2017-08-29 15:27:48.797639

"""

# revision identifiers, used by Alembic.
revision = '2441049ac32c'
down_revision = '1042b15c2c7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('installation', 'kernel_options', existing_type=sa.UnicodeText, nullable=True)


def downgrade():
    op.execute("""
        UPDATE installation
            SET kernel_options = ''
            WHERE kernel_options is NULL
    """)
    op.alter_column('installation', 'kernel_options', existing_type=sa.UnicodeText, nullable=False)

