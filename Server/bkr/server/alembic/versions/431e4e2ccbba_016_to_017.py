# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""migrate from 0.16 to 0.17

Revision ID: 431e4e2ccbba
Revises: 2f38ab976d17
Create Date: 2014-08-04 10:24:42.194910

"""

# revision identifiers, used by Alembic.
revision = '431e4e2ccbba'
down_revision = '2f38ab976d17'

from alembic import op
import sqlalchemy as sa
from bkr.server.model import UUID
from bkr.server.alembic.migration_utils import find_unique

def upgrade():
    op.create_table('openstack_region',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('lab_controller_id', sa.Integer(), nullable=False),
                    sa.Column('ipxe_image_id', sa.Unicode(length=2048), nullable=True),
                    sa.ForeignKeyConstraint(['lab_controller_id'], ['lab_controller.id'],
                        name='openstack_region_lab_controller_id_fk'),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_engine='InnoDB'
    )
    op.create_table('job_activity',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('job_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['id'], ['activity.id'], ),
                    sa.ForeignKeyConstraint(['job_id'], ['job.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_engine='InnoDB'
    )
    op.create_table('recipe_reservation',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('recipe_id', sa.Integer(), nullable=False),
                    sa.Column('duration', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['recipe_id'], ['recipe.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    mysql_engine='InnoDB'
    )
    op.add_column('tg_user', sa.Column('openstack_username', sa.Unicode(length=255), nullable=True))
    op.add_column('tg_user', sa.Column('openstack_password', sa.Unicode(length=2048), nullable=True))
    op.add_column('tg_user', sa.Column('openstack_tenant_name', sa.Unicode(length=2048), nullable=True))
    op.add_column('virt_resource', sa.Column('instance_id', UUID(), nullable=False))
    op.add_column('virt_resource', sa.Column('kernel_options', sa.Unicode(length=2048), nullable=True))
    # drop key email_address
    op.drop_index('email_address', 'tg_user')
    # add index email_address
    op.create_index('email_address', 'tg_user', ['email_address'])
    # Need to replace the user_id index with a unique index, however its name 
    # might be user_id or lab_controller_user_id...
    old_index_name, = [index['name'] for index in
            sa.inspect(op.get_bind()).get_indexes('lab_controller')
            if index['column_names'] == ['user_id']]
    op.execute("ALTER TABLE lab_controller "
            "DROP KEY %s, ADD UNIQUE KEY user_id (user_id)" % old_index_name)
    op.execute("ALTER TABLE job "
               "ADD ntasks INT AFTER ttasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 'Reserved') NOT NULL")
    op.execute("ALTER TABLE recipe_set "
               "ADD ntasks INT AFTER ttasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 'Reserved') NOT NULL")
    op.execute("ALTER TABLE recipe "
               "ADD ntasks INT AFTER ttasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted', 'Reserved') NOT NULL")
    op.alter_column('recipe_task', u'status',
               type_=sa.Enum(u'New', u'Processed', u'Queued', u'Scheduled', u'Waiting', u'Running', u'Completed', u'Cancelled', u'Aborted', u'Reserved'),
               nullable=False)

def downgrade():
    op.drop_table('recipe_reservation')
    op.drop_table('job_activity')
    op.drop_table('openstack_region')
    op.drop_column('virt_resource', 'kernel_options')
    op.drop_column('virt_resource', 'instance_id')
    op.drop_column('tg_user', 'openstack_tenant_name')
    op.drop_column('tg_user', 'openstack_password')
    op.drop_column('tg_user', 'openstack_username')
    op.drop_index('email_address', 'tg_user')
    op.create_unique_constraint('email_address', 'tg_user', ['email_address'])
    # We want to replace the unique constraint on lab_controller.user_id with 
    # an ordinary index. The constraint will be called 'uc_user_id' if it was 
    # created by following the original 0.17 upgrade notes, otherise it will be 
    # called 'user_id'.
    unique_name = find_unique('lab_controller', ['user_id'])
    op.execute("ALTER TABLE lab_controller "
               "DROP KEY %s, ADD KEY user_id (user_id)" % unique_name)
    op.execute("ALTER TABLE job "
               "DROP ntasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted') NOT NULL")
    op.execute("ALTER TABLE recipe_set "
               "DROP ntasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted') NOT NULL")
    op.execute("ALTER TABLE recipe "
               "DROP ntasks,"
               "MODIFY status ENUM('New', 'Processed', 'Queued', 'Scheduled',"
               "'Waiting', 'Running', 'Completed', 'Cancelled', 'Aborted') NOT NULL")
    op.alter_column('recipe_task', u'status',
               existing_type=sa.Enum(u'New', u'Processed', u'Queued', u'Scheduled', u'Waiting', u'Running', u'Completed', u'Cancelled', u'Aborted'),
               nullable=False)
