# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add distro metadata columns to installation

Revision ID: 3ba776df4c76
Revises: 2441049ac32c
Create Date: 2017-11-13 17:48:17.686405

"""

# revision identifiers, used by Alembic.
revision = '3ba776df4c76'
down_revision = '2441049ac32c'

from alembic import op


def upgrade():
    op.execute("""
        ALTER TABLE installation
        ADD COLUMN tree_url TEXT DEFAULT NULL,
        ADD COLUMN initrd_path TEXT DEFAULT NULL,
        ADD COLUMN kernel_path TEXT DEFAULT NULL,
        ADD COLUMN distro_name TEXT DEFAULT NULL,
        ADD COLUMN osmajor TEXT DEFAULT NULL,
        ADD COLUMN osminor TEXT DEFAULT NULL,
        ADD COLUMN variant TEXT DEFAULT NULL,
        ADD COLUMN arch_id INT DEFAULT NULL,
        ADD CONSTRAINT installation_arch_id_fk FOREIGN KEY (arch_id)
            REFERENCES arch (id)
    """)


def downgrade():
    op.execute("""
        ALTER TABLE installation
        DROP COLUMN tree_url,
        DROP COLUMN initrd_path,
        DROP COLUMN kernel_path,
        DROP COLUMN distro_name,
        DROP COLUMN osmajor,
        DROP COLUMN osminor,
        DROP COLUMN variant,
        DROP FOREIGN KEY installation_arch_id_fk,
        DROP COLUMN arch_id
    """)
