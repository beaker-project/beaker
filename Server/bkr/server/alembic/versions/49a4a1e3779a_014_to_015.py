# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Migrate from 0.14 to 0.15

Revision ID: 49a4a1e3779a
Revises: 057b088bfb32
Create Date: 2014-10-09 12:24:58.333096

"""

# revision identifiers, used by Alembic.
revision = '49a4a1e3779a'
down_revision = '057b088bfb32'

from alembic import op
import sqlalchemy as sa

def upgrade():
    # System access policies
    op.create_table('system_access_policy',
        sa.Column('id', sa.Integer, nullable=False, primary_key=True),
        sa.Column('system_id', sa.Integer,
            sa.ForeignKey('system.id', name='system_access_policy_system_id_fk')),
        mysql_engine='InnoDB'
    )
    op.create_table('system_access_policy_rule',
        sa.Column('id', sa.Integer, nullable=False, primary_key=True),
        sa.Column('policy_id', sa.Integer, sa.ForeignKey('system_access_policy.id',
            name='system_access_policy_rule_policy_id_fk'), nullable=False),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('tg_user.user_id',
            name='system_access_policy_rule_user_id_fk')),
        sa.Column('group_id', sa.Integer, sa.ForeignKey('tg_group.group_id',
            name='system_access_policy_rule_group_id_fk')),
        sa.Column('permission', sa.Enum('edit_policy', 'edit_system',
            'loan_any', 'loan_self', 'control_system', 'reserve')),
        mysql_engine='InnoDB'
    )
    op.execute("""
        INSERT INTO system_access_policy (system_id)
        SELECT id FROM system
        WHERE NOT EXISTS (SELECT 1 FROM system_access_policy
            WHERE system_id = system.id)
        """)
    op.execute("""
        INSERT INTO system_access_policy_rule
            (policy_id, user_id, group_id, permission)
        SELECT system_access_policy.id, NULL, NULL, 'control_system'
        FROM system_access_policy
        INNER JOIN system ON system_access_policy.system_id = system.id
        WHERE NOT EXISTS (SELECT 1 FROM system_access_policy_rule
            WHERE policy_id = system_access_policy.id
                AND user_id IS NULL
                AND group_id IS NULL
                AND permission = 'control_system')
        """)
    op.execute("""
        INSERT INTO system_access_policy_rule
            (policy_id, user_id, group_id, permission)
        SELECT system_access_policy.id, NULL, NULL, 'reserve'
        FROM system_access_policy
        INNER JOIN system ON system_access_policy.system_id = system.id
        WHERE shared = TRUE
            AND NOT EXISTS (SELECT 1 FROM system_group
                WHERE system_id = system.id)
            AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
                WHERE policy_id = system_access_policy.id
                    AND user_id IS NULL
                    AND group_id IS NULL
                    AND permission = 'reserve')
        """)
    op.execute("""
        INSERT INTO system_access_policy_rule
            (policy_id, user_id, group_id, permission)
        SELECT system_access_policy.id, NULL, system_group.group_id, 'reserve'
        FROM system_access_policy
        INNER JOIN system ON system_access_policy.system_id = system.id
        INNER JOIN system_group ON system_group.system_id = system.id
        WHERE shared = TRUE
            AND system_group.admin = FALSE
            AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
                WHERE policy_id = system_access_policy.id
                    AND user_id IS NULL
                    AND group_id = system_group.group_id
                    AND permission = 'reserve')
        """)
    op.execute("""
        INSERT INTO system_access_policy_rule
            (policy_id, user_id, group_id, permission)
        SELECT system_access_policy.id, NULL, system_group.group_id, permission.p
        FROM system_access_policy
        INNER JOIN system ON system_access_policy.system_id = system.id
        INNER JOIN system_group ON system_group.system_id = system.id
        JOIN (SELECT 'edit_policy' p
            UNION SELECT 'edit_system' p
            UNION SELECT 'loan_any' p
            UNION SELECT 'loan_self' p
            UNION SELECT 'control_system' p
            UNION SELECT 'reserve' p) permission
        WHERE system_group.admin = TRUE
            AND NOT EXISTS (SELECT 1 FROM system_access_policy_rule
                WHERE policy_id = system_access_policy.id
                    AND user_id IS NULL
                    AND group_id = system_group.group_id
                    AND permission = permission.p)
        """)

    # TurboGears Visit framework
    # These don't contain any important data, just transient login sessions, so 
    # we can safely drop them during upgrade, and re-create them empty during 
    # downgrade.
    op.drop_table('visit')
    op.drop_table('visit_identity')

    # Group name length
    op.alter_column('tg_group', 'group_name',
            type_=sa.Unicode(255), nullable=False)

    # Task RPM filename
    op.alter_column('task', 'rpm', type_=sa.Unicode(255))
    op.create_unique_constraint('rpm', 'task', ['rpm'])

def downgrade():
    # System access policies
    op.drop_table('system_access_policy_rule')
    op.drop_table('system_access_policy')

    # TurboGears Visit framework
    op.create_table('visit',
        sa.Column('visit_key', sa.String(40), primary_key=True),
        sa.Column('created', sa.DateTime, nullable=False),
        sa.Column('expiry', sa.DateTime),
        mysql_engine='InnoDB'
    )
    op.create_table('visit_identity',
        sa.Column('visit_key', sa.String(40), primary_key=True),
        sa.Column('user_id', sa.Integer,
            sa.ForeignKey('tg_user.user_id'), nullable=False),
        sa.Column('proxied_by_user_id', sa.Integer,
            sa.ForeignKey('tg_user.user_id')),
        mysql_engine='InnoDB'
    )

    # Group name length
    op.alter_column('tg_group', 'group_name',
            type_=sa.Unicode(16), nullable=False)

    # Task RPM filename
    op.drop_index('rpm', 'task')
    op.alter_column('task', 'rpm', type_=sa.Unicode(2048))
