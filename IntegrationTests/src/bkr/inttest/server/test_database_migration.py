
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest2 as unittest
import contextlib
import pkg_resources
import sqlalchemy
from turbogears import config
from turbogears.database import metadata
from bkr.server.tools.init import upgrade_db, downgrade_db

def has_initial_sublist(larger, prefix):
    """ Return true iff list *prefix* is an initial sublist of list 
    *larger*. Like .startswith() for lists. """
    if len(prefix) > len(larger):
        return False
    for i, value in enumerate(prefix):
        if larger[i] != value:
            return False
    return True

class MigrationTest(unittest.TestCase):

    maxDiff = None

    def setUp(self):
        # For the database migration tests we use a side database (usually 
        # 'beaker_migration_test') separate from the main one used in tests 
        # (usually 'beaker_test'). This is to avoid interfering with the schema 
        # that is already created and populated at the start of the test run.
        if not config.get('beaker.migration_test_dburi'):
            raise unittest.SkipTest('beaker.migration_test_dburi is not set')
        migration_engine = sqlalchemy.create_engine(
                config.get('beaker.migration_test_dburi'))
        self.migration_metadata = sqlalchemy.MetaData(bind=migration_engine)
        connection = migration_engine.connect()
        db_name = migration_engine.url.database
        connection.execute('DROP DATABASE IF EXISTS %s' % db_name)
        connection.execute('CREATE DATABASE %s' % db_name)
        connection.invalidate() # can't reuse this one

    def test_full_upgrade(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_full_downgrade_then_upgrade(self):
        # The point is to test that the complete *downgrade* sequence is valid, 
        # by then upgrading again and making sure we still have a correct schema.
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.11.sql'))
        upgrade_db(self.migration_metadata)
        downgrade_db(self.migration_metadata, 'base')
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_012(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.12.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_013(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.13.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_014(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.14.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_015(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.15.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_016(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.16.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    def test_from_017(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/0.17.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()

    # These schema dumps are derived from actual dumps from the Red Hat 
    # production Beaker instance at various points in time, which makes 
    # them a more realistic test case than the synthetically generated 
    # schemas used in the cases above.

    def test_redhat_production_20140820(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20140820.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20140109(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20140109.sql'))
        upgrade_db(self.migration_metadata)
        # This one won't pass the check, due to a snafu with task.rpm
        #self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20130304(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20130304.sql'))
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def test_redhat_production_20120216(self):
        connection = self.migration_metadata.bind.connect()
        connection.execute(pkg_resources.resource_string('bkr.inttest.server',
                'database-dumps/redhat-production-20120216.sql'))
        raise unittest.SkipTest('Database migrations are not implemented '
                'far enough into the past yet')
        upgrade_db(self.migration_metadata)
        self.check_migrated_schema()
        downgrade_db(self.migration_metadata, 'base')

    def check_migrated_schema(self):
        """
        Compares the schema in the migrated db (self.migration_metadata) 
        against the fresh one which was populated for this test run (global TG 
        metadata).
        """
        self.migration_metadata.reflect()
        # The upgraded schema will not be *completely identical* to the fresh 
        # one. There are some exceptions because the migrations intentionally 
        # leave behind some structures to avoid destroying data in case the 
        # admin wants to downgrade later. So we have to account for those here.
        expected_tables = metadata.tables.keys()
        expected_tables.append('alembic_version') # it exists, just not in metadata
        actual_tables = self.migration_metadata.tables.keys()
        if 'lab_controller_data_center' in actual_tables:
            # may be left over from 0.16
            actual_tables.remove('lab_controller_data_center')
        self.assertItemsEqual(expected_tables, actual_tables)
        for table_name in metadata.tables:
            expected_columns = metadata.tables[table_name].columns.keys()
            actual_columns = self.migration_metadata.tables[table_name].columns.keys()
            if table_name == 'virt_resource':
                # may be left over from 0.16
                if 'system_name' in actual_columns:
                    actual_columns.remove('system_name')
                if 'mac_address' in actual_columns:
                    actual_columns.remove('mac_address')
            elif table_name == 'system':
                # may be left over from 0.15
                if 'private' in actual_columns:
                    actual_columns.remove('private')
                # may be left over from 0.14
                if 'shared' in actual_columns:
                    actual_columns.remove('shared')
            elif table_name == 'system_group':
                # may be left over from 0.14
                if 'admin' in actual_columns:
                    actual_columns.remove('admin')
            self.assertItemsEqual(expected_columns, actual_columns)
            for column_name in metadata.tables[table_name].columns.keys():
                self.assert_columns_equivalent(
                        metadata.tables[table_name].columns[column_name],
                        self.migration_metadata.tables[table_name].columns[column_name])
            expected_indexes = self.find_expected_indexes_for_table(
                    metadata.tables[table_name])
            actual_indexes = dict((index.name, [col.name for col in index.columns])
                    for index in self.migration_metadata.tables[table_name].indexes)
            if table_name == 'virt_resource':
                if 'ix_virt_resource_mac_address' in actual_indexes:
                    # may be left over from 0.16
                    del actual_indexes['ix_virt_resource_mac_address']
            # These may exist for unknown hysterical raisins (commit 520b4ddd)
            if table_name == 'log_recipe':
                if 'recipe_id_id' in actual_indexes:
                    del actual_indexes['recipe_id_id']
            if table_name == 'log_recipe_task':
                if 'recipe_task_id_id' in actual_indexes:
                    del actual_indexes['recipe_task_id_id']
            if table_name == 'log_recipe_task_result':
                if 'recipe_task_result_id_id' in actual_indexes:
                    del actual_indexes['recipe_task_result_id_id']
            # This was accidentally created in 0.7.1 upgrade (commit 75a9bea9) 
            # but it serves no purpose so we aren't adding it
            if table_name == 'task':
                if 'priority' in actual_indexes:
                    del actual_indexes['priority']
            # For now, we are ignoring differences in index names. That's 
            # because we have a lot of cases where the SA generated name is 
            # ix_<table>_<col> and that will appear in a fresh schema, but an 
            # older upgraded schema will have the MySQL generated name <col>.
            self.assertItemsEqual(expected_indexes.values(),
                    actual_indexes.values(),
                    'Incorrect indexes on %s' % table_name)
            expected_uniques = []
            for constraint in metadata.tables[table_name].constraints:
                if isinstance(constraint, (sqlalchemy.PrimaryKeyConstraint,
                        sqlalchemy.ForeignKeyConstraint)):
                    # PKs and FKs are checked below on individual columns
                    continue
                elif isinstance(constraint, sqlalchemy.CheckConstraint):
                    # SA generates CheckConstraints for ENUM columns but they 
                    # are not actually used in MySQL, so we ignore them
                    continue
                elif isinstance(constraint, sqlalchemy.UniqueConstraint):
                    expected_uniques.append([col.name for col in constraint.columns])
                else:
                    raise AssertionError('Need code to handle %r' % constraint)
            for index in metadata.tables[table_name].indexes:
                if index.unique:
                    expected_uniques.append([col.name for col in index.columns])
            actual_uniques = []
            # In MySQL, all unique constraints become unique indexes
            for index in self.migration_metadata.tables[table_name].indexes:
                if index.unique:
                    actual_uniques.append([col.name for col in index.columns])
            self.assertItemsEqual(expected_uniques, actual_uniques,
                    'Incorrect unique constraints on %s' % table_name)

    def find_expected_indexes_for_table(self, table):
        # This is not as easy as you might think (thanks MySQL...)
        expected_indexes = {}
        for index in table.indexes:
            expected_indexes[index.name] = [col.name for col in index.columns]
        # If we have defined a column with a unique constraint but it is not 
        # explicitly indexed (and is also not the first column in a primary 
        # key), then InnoDB will implicitly create an index on that column. 
        # So there will be some extra indexes which we never explicitly 
        # defined in Python land.
        for constraint in table.constraints:
            if isinstance(constraint, sqlalchemy.UniqueConstraint):
                cols = [col.name for col in constraint.columns]
                if any(has_initial_sublist(index_cols, cols)
                        for index_cols in expected_indexes.values()):
                    continue
                if has_initial_sublist(table.primary_key.columns.values(),
                        constraint.columns.values()):
                    continue
                name = constraint.name or constraint.columns.values()[0].name
                expected_indexes[name] = cols
        # Similarly, if we have defined a foreign key without an 
        # explicit index, InnoDB creates one implicitly.
        for fk in table.foreign_keys:
            if any(index_cols[0] == fk.parent.name
                    for index_cols in expected_indexes.values()):
                continue
            if table.primary_key.columns.values()[0] == fk.parent:
                continue
            expected_indexes[fk.name or fk.parent.name] = [fk.parent.name]
        return expected_indexes

    def assert_columns_equivalent(self, expected, actual):
        self.assertEquals(actual.name, expected.name)
        # actual.type is the dialect-specific type so it will not be identical 
        # to expected.type
        if isinstance(actual.type, sqlalchemy.dialects.mysql.TINYINT):
            self.assertTrue(isinstance(expected.type, sqlalchemy.Boolean),
                    'Actual type was TINYINT which is equivalent to Boolean, '
                    'but expected type was %r' % expected.type)
        else:
            self.assertTrue(actual.type._compare_type_affinity(expected.type),
                    'Actual type %r should be equivalent to expected type %r'
                    % (actual.type, expected.type))
        if hasattr(expected.type, 'length'):
            self.assertEquals(actual.type.length, expected.type.length,
                    '%r has wrong length' % actual)
        if hasattr(expected.type, 'enums'):
            self.assertItemsEqual(actual.type.enums, expected.type.enums)
        self.assertEquals(actual.nullable, expected.nullable,
                '%r should%s be nullable' % (actual,
                '' if expected.nullable else ' not'))
        self.assertEquals(actual.primary_key, expected.primary_key)
        if expected.server_default:
            self.assertEquals(actual.server_default, expected.server_default,
                    '%r has incorrect database default' % actual)
        else:
            if not actual.nullable and actual.server_default:
                # MySQL forces non-NULLable columns to have a default even if 
                # we don't want to specify one, so we just ignore those.
                default_text = str(actual.server_default.arg)
                if default_text not in ["''", "'0'", "0"]:
                    raise AssertionError('%r should not have database default %s'
                            % (actual, default_text))
            else:
                self.assertIsNone(actual.server_default,
                        '%r should not have a database default' % actual)
        actual_fk_targets = set(fk.target_fullname for fk in actual.foreign_keys)
        expected_fk_targets = set(fk.target_fullname for fk in expected.foreign_keys)
        self.assertItemsEqual(actual_fk_targets, expected_fk_targets,
                '%r has incorrect FK targets' % actual)

    def assert_indexes_equivalent(self, expected, actual):
        self.assertEquals(expected.name, actual.name)
        self.assertEquals([col.name for col in expected.columns],
                [col.name for col in actual.columns])
        self.assertEquals(expected.unique, actual.unique)
