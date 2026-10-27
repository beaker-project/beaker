# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Expand size of sshpubkey keytype and ident

Revision ID: c789086a4ba8
Revises: 140c5eea2836
Create Date: 2026-10-27 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c789086a4ba8'
down_revision = '140c5eea2836'


def upgrade():
    # 16 chars is too narrow for modern key types such as
    # ecdsa-sha2-nistp521 and sk-ecdsa-sha2-nistp256@openssh.com,
    # and 63 is too narrow for long key comments.
    op.alter_column('sshpubkey', 'keytype',
                    existing_type=sa.Unicode(16),
                    type_=sa.Unicode(255),
                    existing_nullable=False)
    op.alter_column('sshpubkey', 'ident',
                    existing_type=sa.Unicode(63),
                    type_=sa.Unicode(255),
                    existing_nullable=False)


def downgrade():
    op.alter_column('sshpubkey', 'keytype',
                    existing_type=sa.Unicode(255),
                    type_=sa.Unicode(16),
                    existing_nullable=False)
    op.alter_column('sshpubkey', 'ident',
                    existing_type=sa.Unicode(255),
                    type_=sa.Unicode(63),
                    existing_nullable=False)
