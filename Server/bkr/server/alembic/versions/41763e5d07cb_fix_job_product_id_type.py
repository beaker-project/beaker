# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Fix job.product_id type

Revision ID: 41763e5d07cb
Revises: 2c03c52950bf
Create Date: 2014-10-10 13:22:26.918643

"""

# revision identifiers, used by Alembic.
revision = '41763e5d07cb'
down_revision = '2c03c52950bf'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import find_column_type

def upgrade():
    column_type = find_column_type('job', 'product_id')
    if not isinstance(column_type, sa.Integer):
        op.execute("""
            UPDATE job
            SET product_id = NULL
            WHERE product_id NOT IN (SELECT id FROM product)
            """)
        op.execute("""
            ALTER TABLE job
            MODIFY product_id INT DEFAULT NULL,
            ADD CONSTRAINT job_product_id_fk
                FOREIGN KEY (product_id)
                REFERENCES product (id)
            """)

def downgrade():
    pass # no downgrade as this was a schema mistake
