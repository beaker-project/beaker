# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""remove commands without lab controller

Revision ID: 4f7a4316565f
Revises: 1626ad29c170
Create Date: 2016-10-20 11:41:51.353958

"""

# revision identifiers, used by Alembic.
revision = '4f7a4316565f'
down_revision = '1626ad29c170'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.execute("""
    update command_queue
    set status = 'Aborted'
    where status in ('Queued', 'Running') and
    system_id in (select id from system where lab_controller_id is null)
    """)


def downgrade():
    pass
