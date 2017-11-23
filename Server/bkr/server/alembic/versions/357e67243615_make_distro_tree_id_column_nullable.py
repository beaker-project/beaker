# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""make distro_tree_id column nullable

Revision ID: 357e67243615
Revises: 3ba776df4c76
Create Date: 2017-11-23 10:14:55.165056

"""

# revision identifiers, used by Alembic.
revision = '357e67243615'
down_revision = '3ba776df4c76'

from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE installation
        MODIFY distro_tree_id INT;
    """)


def downgrade():
    op.execute("""
    UPDATE installation
        SET distro_tree_id = (SELECT MIN(id) FROM distro_tree)
        WHERE distro_tree_id IS NULL;
    """)
    op.execute("""
        ALTER TABLE installation
        MODIFY distro_tree_id INT NOT NULL;
    """)