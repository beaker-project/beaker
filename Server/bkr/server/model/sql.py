
from sqlalchemy.sql import Insert, and_
from sqlalchemy.ext import compiler

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
    colparams = compiler._get_colparams(element)
    text = 'INSERT INTO %s' % compiler.process(element.table, asfrom=True)
    text += ' (%s)\n' % ', '.join(compiler.process(c[0]) for c in colparams)
    text += 'SELECT %s\n' % ', '.join(c[1] for c in colparams)
    text += 'FROM DUAL\n'
    # We need FOR UPDATE in the inner SELECT for MySQL, to ensure we acquire an 
    # exclusive lock immediately, instead of acquiring a shared lock and then 
    # subsequently upgrading it to an exclusive lock, which is subject to 
    # deadlocks if another transaction is doing the same thing.
    text += 'WHERE NOT EXISTS (SELECT 1 FROM %s\nWHERE %s FOR UPDATE)' % (
            compiler.process(element.table, asfrom=True),
            compiler.process(element.unique_condition))
    return text
