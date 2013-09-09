# These are unit tests which don't need a MySQL database. Tests which need to
# talk to external services belong in the IntegrationTests subdir.

import unittest
from sqlalchemy.schema import MetaData, Table, Column
from sqlalchemy.types import Integer, Unicode
from bkr.server.model import ConditionalInsert

class ConditionalInsertTest(unittest.TestCase):

    def test_unique_params_only(self):
        metadata = MetaData()
        table = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(16), nullable=False, unique=True),
        )
        clause = ConditionalInsert(table, {table.c.name: 'asdf'})
        compiled = clause.compile()
        self.assertEquals(str(compiled),
                'INSERT INTO "table" ("table".name)\n'
                'SELECT :name\nFROM DUAL\nWHERE NOT EXISTS '
                '(SELECT 1 FROM "table"\nWHERE "table".name = :name_1 FOR UPDATE)')
        self.assertEquals(compiled.params, {'name': 'asdf', 'name_1': 'asdf'})

    def test_with_extra_params(self):
        metadata = MetaData()
        table = Table('table', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', Unicode(16), nullable=False, unique=True),
            Column('extra', Unicode(16), nullable=False),
        )
        clause = ConditionalInsert(table, {table.c.name: 'asdf'},
                {table.c.extra: 'something'})
        compiled = clause.compile()
        self.assertEquals(str(compiled),
                'INSERT INTO "table" ("table".name, "table".extra)\n'
                'SELECT :name, :extra\nFROM DUAL\nWHERE NOT EXISTS '
                '(SELECT 1 FROM "table"\nWHERE "table".name = :name_1 FOR UPDATE)')
        self.assertEquals(compiled.params, {'name': 'asdf',
                'extra': 'something', 'name_1': 'asdf'})
