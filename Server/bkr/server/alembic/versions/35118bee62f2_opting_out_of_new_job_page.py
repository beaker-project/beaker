# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add column for opting out of new job page

Revision ID: 35118bee62f2
Revises: 0ae85f81f838
Create Date: 2016-02-02 11:16:21.215329

"""

# revision identifiers, used by Alembic.
revision = '35118bee62f2'
down_revision = '0ae85f81f838'

from alembic import op
from sqlalchemy import Column, Boolean

def upgrade():
    op.add_column('tg_user', Column('use_old_job_page', Boolean, nullable=False))
    op.execute('UPDATE tg_user SET use_old_job_page = FALSE')

def downgrade():
    op.drop_column('tg_user', 'use_old_job_page')
