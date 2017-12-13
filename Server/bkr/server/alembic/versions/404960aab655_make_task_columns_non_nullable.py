# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Make task columns non-NULLable

Revision ID: 404960aab655
Revises: 17c55b3225a9
Create Date: 2017-12-13 16:52:07.203232
"""

# revision identifiers, used by Alembic.
revision = '404960aab655'
down_revision = '17c55b3225a9'

from alembic import op

def upgrade():
    # Previously, update_date was only set when the row was UPDATE'd meaning it 
    # would be left as NULL if a task was never touched after it was 
    # first uploaded.
    op.execute("""
        UPDATE task
        SET update_date = creation_date
        WHERE update_date IS NULL
        """)
    # Very old tasks may have NULLs here
    op.execute("""
        UPDATE task
        SET rpm = CONCAT('nonexistent-rpm-', id)
        WHERE rpm IS NULL
        """)
    op.execute("""
        UPDATE task
        SET owner = ''
        WHERE owner IS NULL
        """)
    op.execute("""
        ALTER TABLE task
        MODIFY name VARCHAR(255) NOT NULL,
        MODIFY rpm VARCHAR(255) NOT NULL,
        MODIFY path VARCHAR(4096) NOT NULL,
        MODIFY description VARCHAR(2048) NOT NULL,
        MODIFY avg_time INT NOT NULL,
        MODIFY creation_date DATETIME NOT NULL,
        MODIFY update_date DATETIME NOT NULL,
        MODIFY owner VARCHAR(255) NOT NULL,
        MODIFY version VARCHAR(256) NOT NULL,
        MODIFY license VARCHAR(256) NOT NULL
        """)

def downgrade():
    op.execute("""
        ALTER TABLE task
        MODIFY name VARCHAR(255),
        MODIFY rpm VARCHAR(255),
        MODIFY path VARCHAR(4096),
        MODIFY description VARCHAR(2048),
        MODIFY avg_time INT,
        MODIFY creation_date DATETIME,
        MODIFY update_date DATETIME,
        MODIFY owner VARCHAR(255),
        MODIFY version VARCHAR(256),
        MODIFY license VARCHAR(256)
        """)
