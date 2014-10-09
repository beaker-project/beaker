# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Migrate from 0.13 to 0.14

Revision ID: 057b088bfb32
Revises: 41aa3372239e
Create Date: 2014-10-09 12:48:26.353347

"""

# revision identifiers, used by Alembic.
revision = '057b088bfb32'
down_revision = '41aa3372239e'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('submission_delegate',
        sa.Column('id', sa.Integer, nullable=False, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('tg_user.user_id',
            name='tg_user_id_fk1'), nullable=False),
        sa.Column('delegate_id', sa.Integer, sa.ForeignKey('tg_user.user_id',
            name='tg_user_id_fk2'), nullable=False),
        sa.UniqueConstraint('user_id', 'delegate_id'),
        mysql_engine='InnoDB'
    )
    op.execute("""
        ALTER TABLE job
        ADD COLUMN submitter_id INT DEFAULT NULL,
        ADD CONSTRAINT job_submitter_id_fk
            FOREIGN KEY (submitter_id)
            REFERENCES tg_user (user_id)
        """)
    op.create_table('user_activity',
        sa.Column('id', sa.Integer, sa.ForeignKey('activity.id'),
            primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('tg_user.user_id'),
            nullable=False),
        mysql_engine='InnoDB'
    )

def downgrade():
    op.execute("""
        ALTER TABLE job
        DROP FOREIGN KEY job_submitter_id_fk,
        DROP submitter_id
        """)
    op.drop_table('submission_delegate')
    op.drop_table('user_activity')
