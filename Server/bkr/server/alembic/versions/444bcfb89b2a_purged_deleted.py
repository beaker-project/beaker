# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Rename deleted -> purged, to_delete -> deleted

Revision ID: 444bcfb89b2a
Revises: 1a7dec79baa4
Create Date: 2017-07-27 14:00:54.999573
"""

# revision identifiers, used by Alembic.
revision = '444bcfb89b2a'
down_revision = '1a7dec79baa4'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("""
        ALTER TABLE job
        CHANGE deleted purged DATETIME DEFAULT NULL,
        CHANGE to_delete deleted DATETIME DEFAULT NULL
        """)
    # This part is not reversible, but it doesn't matter because the old code
    # treated a job as deleted if *either* deleted or to_delete were set.
    op.execute("""
        UPDATE job
        SET deleted = purged
        WHERE deleted IS NULL AND purged IS NOT NULL
        """)

def downgrade():
    op.execute("""
        ALTER TABLE job
        CHANGE deleted to_delete DATETIME DEFAULT NULL,
        CHANGE purged deleted DATETIME DEFAULT NULL
        """)
