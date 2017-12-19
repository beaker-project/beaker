
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Plugin for pylint to make it aware of some Beaker-specific stuff and/or to work 
around false failures due to various libraries Beaker is using.
"""

import astroid

def register(linter):
    pass

def socket_extend():
    return astroid.parse('''
        class socket(object):
            def sendto(self, string, address): pass
            def settimeout(self, timeout): pass
        ''')

def krbV_extend():
    return astroid.parse('''
        class Krb5Error(Exception):
            err_code = 0
            message = ''
        ''')

def sqlalchemy_orm_scoping_extend():
    return astroid.parse('''
        from sqlalchemy.util import ScopedRegistry
        from sqlalchemy.orm.session import Session
        from sqlalchemy.orm.query import Query
        class scoped_session(Session):
            registry = ScopedRegistry(Session)
            def query_property(self):
                return Query()
        ''')

def alembic_context_extend():
    """
    Alembic encourages you to import and use module-scope functions everywhere, 
    but then uses magic to proxy those to a global instance of some class... 
    sigh. This fake definition is not authoritative but it covers everything we 
    use currently.
    """
    return astroid.parse('''
        def configure(**kwargs): pass
        def begin_transaction(): pass
        def run_migrations(**kwargs): pass
        def is_offline_mode(): return True
        ''')

def alembic_op_extend():
    """
    As above.
    """
    return astroid.parse('''
        import sqlalchemy.engine
        def alter_column(table_name, column_name, **kwargs): pass
        def create_foreign_key(constraint_name, source_table, referent_table, local_cols, remote_cols, **kwargs): pass
        def create_unique_constraint(constraint_name, table_name, columns, **kwargs): pass
        def drop_index(index_name, table_name): pass
        def drop_constraint(constraint_name, table_name, **kwargs): pass
        def get_bind(): return sqlalchemy.engine.Connection()
        ''')

def formencode_api_extend():
    """
    The _to_python and _from_python methods are deprecated in newer formencode 
    but they still work. formencode.api.FancyValidator.__classinit__ uses some 
    magic to fill them in when needed.
    """
    return astroid.parse('''
        class FancyValidator(Validator):
            if_empty = False
            not_empty = False
            strip = False
            if_invalid = ''
            if_invalid_python = None
            accept_python = False
            def _convert_to_python(self, value, state=None): return value
            _to_python = _convert_to_python
            def _convert_from_python(self, value, state=None): return value
            _from_python = _convert_from_python
            validate_python = _validate_python
            validate_other = _validate_other
        ''')

def gevent_socket_extend():
    return astroid.parse('''
        def wait_read(fileno, timeout=None, timeout_exc=None): pass
        ''')

def lxml_builder_extend():
    return astroid.parse('''
        import lxml.etree
        def _make(tag, *args, **kwargs):
            return lxml.etree.Element()
        class ElementMaker(object):
            def __call__(self, name, *args, **kwargs):
                return _make(name, *args, **kwargs)
            def __getattr__(self, name):
                return True
        E = ElementMaker()
        ''')

def lxml_builder_transform(node):
    if node.name == 'lxml.builder':
        # This is a lie (lxml.builder *is* a Cython compiled module since
        # lxml 4.0, it's not pure Python) but we need it to convince pylint 
        # that the ElementMaker.__getattr__ method is actually real. Astroid's 
        # has_dynamic_getattr() method intentionally ignores a __getattr__ 
        # method which is present in compiled modules under the assumption that 
        # it's just a slot that is not necessarily implemented.
        # https://github.com/PyCQA/astroid/commit/a709fa17650d83d0caea78981e65454cea69f27a
        node.pure_python = True

def beaker_decl_enum_transform(cls):
    """
    DeclEnum uses some metaclass magic to fill in values as attributes on the type,
    based on the 'symbols' class attribute.
    """
    if cls.is_subtype_of('bkr.server.enum.DeclEnum') and cls.name != 'DeclEnum':
        symbols = eval(cls.locals['symbols'][0].statement().value.as_string(), {'_': lambda x: x})
        for pyname, dbname, attrs in symbols:
            cls.locals[pyname] = dbname

astroid.register_module_extender(astroid.MANAGER, 'socket', socket_extend)
astroid.register_module_extender(astroid.MANAGER, 'krbV', krbV_extend)
astroid.register_module_extender(astroid.MANAGER, 'sqlalchemy.orm.scoping', sqlalchemy_orm_scoping_extend)
astroid.register_module_extender(astroid.MANAGER, 'alembic.context', alembic_context_extend)
astroid.register_module_extender(astroid.MANAGER, 'alembic.op', alembic_op_extend)
astroid.register_module_extender(astroid.MANAGER, 'formencode.api', formencode_api_extend)
# XXX should be registered for 'gevent.socket' but pylint gets confused
astroid.register_module_extender(astroid.MANAGER, 'socket', gevent_socket_extend)
astroid.register_module_extender(astroid.MANAGER, 'lxml.builder', lxml_builder_extend)
astroid.MANAGER.register_transform(astroid.ClassDef, beaker_decl_enum_transform)
astroid.MANAGER.register_transform(astroid.Module, lxml_builder_transform)
