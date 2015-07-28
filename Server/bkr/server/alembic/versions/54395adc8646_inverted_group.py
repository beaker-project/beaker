# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Add support for inverted groups

Revision ID: 54395adc8646
Revises: 362bb6508a2b
Create Date: 2015-12-07 11:12:23.363705

"""

# revision identifiers, used by Alembic.
revision = '54395adc8646'
down_revision = '362bb6508a2b'

from alembic import op
import sqlalchemy as sa
from bkr.server.alembic.migration_utils import drop_fk


def upgrade():
    op.add_column('tg_group', sa.Column('membership_type', sa.Enum(u'normal',
            u'ldap', u'inverted'), nullable=False))
    op.create_index('ix_tg_group_membership_type', 'tg_group', ['membership_type'])
    # Before dropping the ldap column, we need to migrate the existing LDAP
    # groups.
    op.execute("""
        UPDATE tg_group
        SET membership_type = 'ldap'
        WHERE ldap = 1
    """)
    op.drop_column('tg_group', 'ldap')
    op.create_table('excluded_user_group',
        sa.Column('user_id', sa.Integer(), nullable=False, index=True),
        sa.Column('group_id', sa.Integer(), nullable=False, index=True),
        sa.ForeignKeyConstraint(['group_id'], ['tg_group.group_id'],
                                name='excluded_user_group_group_id_fk',
                                onupdate='CASCADE', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['tg_user.user_id'],
                                name='excluded_user_group_user_id_fk',
                                onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'group_id'),
        mysql_engine='InnoDB'
    )

def downgrade():
    op.add_column('tg_group', sa.Column('ldap', sa.Boolean,
            nullable=False, server_default=u'0'))
    op.create_index('ix_tg_group_ldap', 'tg_group', ['ldap'])
    op.execute("""
        UPDATE tg_group
        SET ldap = 1
        WHERE membership_type = 'ldap'
    """)
    op.drop_column('tg_group', 'membership_type')
    op.drop_table('excluded_user_group')
