# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Replace job dirty_version/clean_version with is_dirty

Revision ID: 4d4e0a92ee10
Revises: 1ce53a2af0ed
Create Date: 2018-06-04 17:04:35.679835

"""

# revision identifiers, used by Alembic.
revision = '4d4e0a92ee10'
down_revision = '1ce53a2af0ed'

from alembic import op
from sqlalchemy import Column, Boolean

def upgrade():
    op.add_column('job', Column('is_dirty', Boolean(create_constraint=False), nullable=True))
    op.execute("""
        UPDATE job
        SET is_dirty = (dirty_version != clean_version)
        """)
    op.execute("""
        ALTER TABLE job
        MODIFY is_dirty TINYINT NOT NULL,
        ADD KEY ix_job_is_dirty (is_dirty),
        DROP KEY ix_job_dirty_clean_version,
        DROP dirty_version,
        DROP clean_version
        """)

def downgrade():
    op.execute("""
        ALTER TABLE job
        ADD dirty_version BINARY(16),
        ADD clean_version BINARY(16),
        ADD KEY ix_job_dirty_clean_version (dirty_version, clean_version)
        """)
    op.execute("""
        UPDATE job
        SET dirty_version = '0000000000000000',
        clean_version = CASE WHEN is_dirty THEN '1111111111111111' ELSE '0000000000000000' END
        """)
    op.execute("""
        ALTER TABLE job
        MODIFY dirty_version BINARY(16) NOT NULL,
        MODIFY clean_version BINARY(16) NOT NULL,
        DROP is_dirty
        """)
