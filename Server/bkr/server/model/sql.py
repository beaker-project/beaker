
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.sql import Insert, Select, and_, not_, exists
from sqlalchemy.sql import text as sqltext
from sqlalchemy.ext import compiler
from sqlalchemy.dialects.mysql.base import MySQLDialect

class ConditionalInsert(Insert):
    def __init__(self, table, unique_values, extra_values=()):
        """
        An INSERT statement which will atomically insert a row with the given 
        values if one does not exist, or otherwise do nothing. extra_values are 
        values which do not participate in the unique identity of the row.

        unique_values and extra_values are dicts of (column -> scalar).
        """
        values = dict(unique_values)
        values.update(extra_values)
        super(ConditionalInsert, self).__init__(table, values)
        self.unique_condition = and_(*[col == value
                for col, value in unique_values.iteritems()])

@compiler.compiles(ConditionalInsert)
def visit_conditional_insert(element, compiler, **kwargs):
    # magic copied from sqlalchemy.sql.compiler.SQLCompiler.visit_insert
    compiler.isinsert = True
    try:
        # pylint: disable=E0611
        from sqlalchemy.sql import crud
        colparams = crud._get_crud_params(compiler, element)
    except ImportError:  # SQLAlchemy <= 1.0
        colparams = compiler._get_colparams(element)
    text = 'INSERT INTO %s' % compiler.process(element.table, asfrom=True)
    text += ' (%s)\n' % ', '.join(compiler.preparer.format_column(c[0])
            for c in colparams)
    text += 'SELECT %s\n' % ', '.join(c[1] for c in colparams)
    text += compiler.default_from()
    # default_from() returns '' for MySQL but that's wrong, MySQL requires 
    # FROM DUAL if there is a following WHERE clause.
    if isinstance(compiler.dialect, MySQLDialect):
        text += 'FROM DUAL\n'
    # We need FOR UPDATE in the inner SELECT for MySQL, to ensure we acquire an 
    # exclusive lock immediately, instead of acquiring a shared lock and then 
    # subsequently upgrading it to an exclusive lock, which is subject to 
    # deadlocks if another transaction is doing the same thing.
    nonexistence_clause = not_(exists(Select(
            columns=[sqltext('1')], from_obj=[element.table],
            whereclause=element.unique_condition, for_update=True)))
    text += 'WHERE ' + compiler.process(nonexistence_clause)
    return text
