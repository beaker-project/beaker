
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import decimal
import bkr.server.model as model
import re
import sqlalchemy
from copy import copy
from turbogears import flash
import sqlalchemy.types
from sqlalchemy import or_, and_, not_
from sqlalchemy.sql import visitors, select
from sqlalchemy.sql.expression import true, false
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import aliased, joinedload
from turbogears.database import session
from bkr.server.model import Key as KeyModel
from bkr.common.bexceptions import BeakerException
import logging
log = logging.getLogger(__name__)

def get_alias_target(aliased_class):
    # SQLAlchemy 0.8+ has a proper inspection API,
    # on earlier versions we just hack it
    try:
        from sqlalchemy import inspect
    except ImportError:
        return aliased_class._AliasedClass__target
    return inspect(aliased_class).mapper.entity #pylint: disable=E1102

def _lucene_coerce_for_column(column, term):
    if isinstance(column.type, sqlalchemy.types.Boolean):
        # Solr stores boolean fields as "true"/"false" so let's follow that
        if term.lower() == 'true':
            return True
        elif term.lower() == 'false':
            return False
        else:
            raise ValueError()
    if isinstance(column.type, sqlalchemy.types.Integer):
        return int(term)
    elif isinstance(column.type, sqlalchemy.types.Numeric):
        try:
            return decimal.Decimal(term)
        except decimal.InvalidOperation:
            raise ValueError()
    elif isinstance(column.type, sqlalchemy.types.DateTime):
        return datetime.datetime.strptime(term, '%Y-%m-%d')
    else: # treat everything else as a string
        return term

class _LuceneTermQuery(object):

    def __init__(self, text):
        self.text = text

    def apply(self, column):
        if self.text == u'*':
            return column != None
        try:
            value = _lucene_coerce_for_column(column, self.text)
        except ValueError:
            return false()
        if isinstance(column.type, sqlalchemy.types.DateTime):
            # date searches are implicitly a range across one day
            return and_(column >= value,
                    column <= value.replace(hour=23, minute=59, second=59))
        if isinstance(column.type, sqlalchemy.types.String) and '*' in value:
            return column.like(value.replace('*', '%'))
        return column == value

class _LuceneRangeQuery(object):

    def __init__(self, start, end, start_inclusive, end_inclusive):
        self.start = start
        self.end = end
        self.start_inclusive = start_inclusive
        self.end_inclusive = end_inclusive

    def apply(self, column):
        if self.start == u'*':
            start_clause = true()
        else:
            try:
                start_value = _lucene_coerce_for_column(column, self.start)
            except ValueError:
                start_clause = false()
            else:
                if self.start_inclusive:
                    start_clause = column >= start_value
                else:
                    start_clause = column > start_value
        if self.end == u'*':
            end_clause = true()
        else:
            try:
                end_value = _lucene_coerce_for_column(column, self.end)
            except ValueError:
                end_clause = false()
            else:
                if isinstance(end_value, datetime.datetime):
                    end_value = end_value.replace(hour=23, minute=59, second=59)
                if self.end_inclusive:
                    end_clause = column <= end_value
                else:
                    end_clause = column < end_value
        return and_(start_clause, end_clause)

def _apply_lucene_query(lucene_query, chain):
    if not isinstance(chain, tuple):
        return lucene_query.apply(chain)
    if len(chain) == 1:
        return lucene_query.apply(chain[0])
    else:
        return chain[0].any(_apply_lucene_query(lucene_query, chain[1:]))

_lucene_query_pattern = re.compile(r"""
    (?P<negation>-)?
    (?:(?P<field>[^'"\s]+):)?
    (?:['"](?P<quoted_term>[^'"]*)['"]
    |  (?P<range_term>[\[{] \s* (?P<range_start>[^\]}]*) \s+ TO \s+ (?P<range_end>[^\]}]*) \s* [\]}])
    |  (?P<malformed_range>[\[{] [^\]}]* [\]}])
    |  (?P<term>\S+)
    )""",
    re.VERBOSE)

def lucene_to_sqlalchemy(querystring, search_columns, default_columns):
    """
    Parses the given *querystring* using a Lucene-like syntax and converts it 
    to a SQLAlchemy filter clause.

    http://lucene.apache.org/core/3_6_0/queryparsersyntax.html

    The *search_columns* parameter is a dict of field names from the query 
    string mapped to column definitions. A column definition can be either:

        * A regular SQLAlchemy column or column property (or any other 
          compatible construct). For example, User.user_name. This is used for 
          columns which are selected directly by the query or in a one-to-one 
          join which is applied to the query, for example
          System.query.join(System.user).

        * A tuple making a chain of relationships ending in a single column:
            (relationship_1, ..., relationship_N, column)
          For example, (Group.users, User.user_name). This is used for 
          one-to-many relationships which must be filtered using .any() to 
          produce an EXISTS clause.

    The *default_columns* parameter is a list of column definitions (as above) 
    which will be used for matching terms in the query string which don't have 
    an explicit field name.

    Maybe one day we will be using Lucene/Solr for real...
    """
    # This only understands the subset of Lucene syntax used by the search 
    # bar. In particular, grouping using parentheses is not supported.
    # We should probably use a proper parser instead of a hacky regexp.
    clauses = []
    for match in _lucene_query_pattern.finditer(querystring):
        if match.group('range_term') is not None:
            start = match.group('range_start')
            end = match.group('range_end')
            start_inclusive = match.group('range_term').startswith('[')
            end_inclusive = match.group('range_term').endswith(']')
            lucene_query = _LuceneRangeQuery(start, end,
                    start_inclusive, end_inclusive)
        elif match.group('malformed_range') is not None:
            lucene_query = _LuceneTermQuery(match.group('malformed_range'))
        elif match.group('quoted_term') is not None:
            lucene_query = _LuceneTermQuery(match.group('quoted_term'))
        else:
            lucene_query = _LuceneTermQuery(match.group('term'))
        if match.group('field') is None:
            alternatives = []
            for column in default_columns:
                alternatives.append(_apply_lucene_query(lucene_query, column))
            clause = or_(*alternatives)
        elif match.group('field') in search_columns:
            column = search_columns[match.group('field')]
            clause = _apply_lucene_query(lucene_query, column)
        else:
            clause = false()
        if match.group('negation'):
            clause = not_(clause)
        clauses.append(clause)
    return and_(*clauses)

class MyColumn(object):
    """
    MyColumn is a class to hold information about a mapped column, 
    such as the actual mapped column, the type, and a relation it may
    have to another mapped object

    It should be overridden by classes that will consistently use a
    relation to another mapped object.
    """
    def __init__(self,relations=None, col_type=None,
            column_name=None, column=None, eagerload=True, aliased=True,
            hidden=False, **kw):
            if type(col_type) != type(''):
                raise TypeError('col_type var passed to %s must be string' % self.__class__.__name__)

            self._column = column
            self._type = col_type
            self._relations = relations
            self._column_name = column_name
            self._eagerload = eagerload
            self._aliased = aliased
            # Hidden columns are for backwards compatibility, we honour 
            # searches using them but we don't offer the column in the UI.
            self.hidden = hidden

    def column_join(self, query):
        return_query = None
        onclause = getattr(self, 'onclause', None)
        if onclause and self.relations:
            relation = self.relations.pop()
            if self.eagerload:
                query = query.options(joinedload(onclause))
            return_query = query.outerjoin((relation, onclause))
        elif self.relations:
            if isinstance(self.relations, list):
                if self.eagerload:
                    query = query.options(joinedload(*self.relations))
                return_query = query.outerjoin(*self.relations)
            else:
                if self.eagerload:
                    query = query.options(joinedload(self.relations))
                return_query = query.outerjoin(self.relations)
        else:
            raise ValueError('Cannot join with nothing to join on')
        return return_query

    @property
    def column_name(self):
        return self._column_name

    @property
    def eagerload(self):
        return self._eagerload

    @property
    def type(self):
        return self._type

    @property
    def relations(self):
        return self._relations

    @property
    def column(self):
        return self._column

    @property
    def aliased(self):
        return self._aliased

    @property
    def parent_entity(self):
        try:
            return self.column.parent.entity
        except AttributeError: # sqlalchemy < 0.8
            return self.column.parententity


class CpuColumn(MyColumn):
    """
    CpuColumn defines a relationship to system
    """
    def __init__(self,**kw):
        if not kw.has_key('relations'):
            kw['relations'] = 'cpu'
        super(CpuColumn,self).__init__(**kw)

class DeviceColumn(MyColumn):
    """
    DeviceColumn defines a relationship to system
    """
    def __init__(self,**kw):
        if not kw.has_key('relations'):
            kw['relations'] = 'devices'
        super(DeviceColumn,self).__init__(**kw)        

class DiskColumn(MyColumn):
    def __init__(self, **kwargs):
        kwargs.setdefault('relations', ['disks'])
        super(DiskColumn, self).__init__(**kwargs)

class AliasedColumn(MyColumn):

    def __init__(self, **kw):
        if 'column_name' not in kw:
            raise ValueError('an AliasedColumn must have a column_name')
        relations = kw['relations']
        target_table = kw.get('target_table')
        if not callable(relations): # We can check it's contents
            if len(relations) > 1 and not target_table:
                raise ValueError('Multiple relations specified, '
                   + 'which one to filter on has not been specified')
            if len(set(relations)) != len(relations):
                raise ValueError('There can be no duplicates in table')
        self.target_table = target_table
        onclause = kw.get('onclause')
        if onclause and len(relations) > 1:
            raise ValueError('You can only pass one relation if using an onclause')
        self.onclause = onclause
        super(AliasedColumn, self).__init__(**kw)

    @property
    def relations(self):
        return self._relations

    @property
    def column(self):
        return self._column

    @relations.setter
    def relations(self, val):
        self._relations = val

    @column.setter
    def column(self, val):
        self._column = val


class KeyColumn(AliasedColumn):

    def __init__(self, **kw):
        kw['relations'].append(model.Key)
        kw['column_name'] = 'key_value'
        super(KeyColumn, self).__init__(**kw)


class KeyStringColumn(KeyColumn):

    def __init__(self, **kw):
        kw['target_table'] = model.Key_Value_String
        kw['relations'] = [model.Key_Value_String]
        kw['col_type'] = 'string'
        super(KeyStringColumn, self).__init__(**kw)

    def column_join(self, query):
        """
        column_join is used here to specify the oncaluse for the
        KeyValueString to Key join.
        """
        relations = self.relations
        for relation in relations:
            if get_alias_target(relation) == model.Key:
                key_ = relation
            if get_alias_target(relation) == model.Key_Value_String:
                key_string = relation
        return query.outerjoin((key_string, key_string.system_id==model.System.id),
            (key_, key_.id==key_string.key_id))


class KeyIntColumn(KeyColumn):

    def __init__(self, **kw):
        kw['target_table'] = model.Key_Value_Int
        kw['relations'] = [model.Key_Value_Int]
        kw['col_type'] = 'int'
        super(KeyIntColumn, self).__init__(**kw)

    def column_join(self, query):
        """
        column_join is used here to specify the oncaluse for the
        KeyValueString to Key join.
        """
        relations = self.relations
        for relation in relations:
            if get_alias_target(relation) == model.Key:
                key_ = relation
            if get_alias_target(relation) == model.Key_Value_Int:
                key_int = relation
        return query.outerjoin((key_int, key_int.system_id==model.System.id),
            (key_, key_.id==key_int.key_id))


class KeyCreator(object):
    """
    KeyCreator takes care of determining what key column needs
    to be created.
    """

    INT = 0
    STRING = 1

    @classmethod
    def create(cls, type, **kw):
        if type is cls.STRING:
            obj = KeyStringColumn(**kw)
        elif type is cls.INT:
            obj = KeyIntColumn(**kw)
        else:
            raise ValueError('Key type needs to be either INT or STRING')
        return obj


class Modeller(object):
    """ 
    Modeller class provides methods relating to different datatypes and 
    operations available to those datatypes
    """
    def __init__(self):
        self.structure = {'string' : {'is' : lambda x,y: self.equals(x,y),
                                       'is not' : lambda x,y: self.not_equal(x,y),
                                       'contains' : lambda x,y: self.contains(x,y), },

                          'text' : {'is' : lambda x,y: self.equals(x,y),
                                        'is not' : lambda x,y: self.not_equal(x,y),
                                        'contains' : lambda x,y: self.contains(x,y), },
                                               
                          'integer' : {'is' : lambda x,y: self.equals(x,y), 
                                       'is not' : lambda x,y: self.not_equal(x,y),
                                       'less than' : lambda x,y: self.less_than(x,y),
                                       'greater than' : lambda x,y: self.greater_than(x,y), },
                             
                          'unicode' : {'is' : lambda x,y: self.equals(x,y),
                                       'is not' : lambda x,y: self.not_equal(x,y),
                                       'contains' : lambda x,y: self.contains(x,y), },
                          
                          'boolean' : {'is' : lambda x,y: self.bool_equals(x,y),
                                       'is not' : lambda x,y: self.bool_not_equal(x,y), },  
                          
                          'date' : {'is' : lambda x,y: self.equals(x,y),
                                    'after' : lambda x,y: self.greater_than(x,y),
                                    'before' : lambda x,y: self.less_than(x,y),},

                          'generic' : {'is' : lambda x,y: self.equals(x,y) ,
                                       'is not': lambda x,y:  self.not_equal(x,y), },
                         } 
 
    def less_than(self,x,y):
        return x < y

    def greater_than(self,x,y):
        return x > y
 
    def bool_not_equal(self,x,y):
        bool_y = int(y)
        return x != bool_y

    def bool_equals(self,x,y): 
        bool_y = int(y) 
        return x == bool_y

    def not_equal(self,x,y): 
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard
            return not_(x.like(wildcard_y))
        if not y:
            return and_(x != None,x != y)
        return or_(x != y, x == None)

    def equals(self,x,y):    
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard
            return x.like(wildcard_y)
        if not y:
            return or_(x == None,x==y)
        return x == y

    def contains(self,x,y): 
        return x.like('%%%s%%' % y )
 
    def return_function(self,type,operator,loose_match=True):
        """
        return_function will return the particular python function to be applied to a type/operator combination 
        (i.e sqlalchemy.types.Integer and 'greater than')
        """
        try:
            op_dict = self.structure[type]   
        except KeyError, (error):
            if loose_match:
                op_dict = self.loose_type_match(type)            
            if not op_dict: 
                op_dict = self.structure['generic']
        try: 
            return op_dict[operator]
        except KeyError,e:
            flash(_('%s is not a valid operator' % operator))
            raise

    def return_operators(self,field_type,loose_match=True): 
        # loose_match flag will specify if we should try and 'guess' what data type it is 
        # int,integer,num,number,numeric will match for an integer.
        # string, word match for sqlalchemy.types.string
        # bool,boolean will match for sqlalchemy.types.boolean
        operators = None
        field_type = field_type.lower()
        try:
            operators = self.structure[field_type] 
        except KeyError, (error):
            if loose_match: 
                operators = self.loose_type_match(field_type)    
            if operators is None:
                operators = self.structure['generic'] 
           
        return operators.keys() 
          
    def loose_type_match(self,field_type):
        type_lower = field_type.lower()
        int_pattern = '^int(?:eger)?$|^num(?:ber|eric)?$'  
        string_pattern = '^string$|^word$'          
        bool_pattern = '^bool(?:ean)?$'
        operators = None
        if re.match(int_pattern,type_lower):
            operators = self.structure['integer']
        elif re.match(string_pattern,type_lower):
            operators = self.structure['string']
        elif re.match(bool_pattern,type_lower):
            operators = self.structure['boolean']
        return operators
        
class Search(object):

    def __init__(self, query):
        self.queri = query

    @classmethod
    def get_search_options_worker(cls,search,col_type):
        return_dict = {}
        #Determine what field type we are dealing with. If it is Boolean, convert our values to 0 for False
        # and 1 for True 
        if col_type.lower() == 'boolean':
            search['values'] = { 0:'False', 1:'True'}

        #Determine if we have search values. If we do, then we should only have the operators
        # 'is' and 'is not'.
        if search['values']:
            search['operators'] = filter(lambda x: x == 'is' or x == 'is not', search['operators'])

        search['operators'].sort()
        return_dict['search_by'] = search['operators'] 
        return_dict['search_vals'] = search['values'] 
        return return_dict

    @classmethod
    def get_search_options(cls, table_field, *args, **kw):
        field = table_field
        search = cls.search_on(field)
        col_type = cls.field_type(field)
        return cls.get_search_options_worker(search,col_type)

    def append_results(self,value,column,operation,**kw): 
        value = value.strip()
        pre = self.pre_operations(column,operation,value,**kw)
        cls_name = re.sub('Search','',self.__class__.__name__)
        cls = globals()[cls_name]  
        try:
            mycolumn = cls.searchable_columns[column]
        except KeyError,e:
            flash(_(u'%s is not a valid search criteria' % column)) 
            raise
        self.do_joins(mycolumn)
             
        try: 
            if pre['col_op_filter']:
                filter_func = pre['col_op_filter']
                filter_final = lambda: filter_func(mycolumn.column,value)
            else: 
                filter_final = self.return_standard_filter(mycolumn,operation,value)
        except KeyError,e:
            log.error(e)
            return self.queri
        except AttributeError,e:
            log.error(e)
            return self.queri
        self.queri = self.queri.filter(filter_final())

    def return_results(self):
        return self.queri

    def do_joins(self,mycolumn):
        if mycolumn.relations: 
            try:
                #This column has specified it needs a join, so let's add it to the all the joins
                #that are pertinent to this class. We do this so there is only one point where we add joins 
                #to the query
                #cls_ref.joins.add_join(col_string = str(column),join=mycolumn.join)
                relations = mycolumn.relations
                aliased = mycolumn.aliased
                if not isinstance(relations, list):
                    self.queri = self.queri.outerjoin(relations, aliased=aliased)
                else:
                    for relation in relations:
                        if isinstance(relation, list):
                            self.queri = self.queri.outerjoin(*relation, aliased=aliased)
                        else:
                            self.queri = self.queri.outerjoin(*relations, aliased=aliased)
                            break
            except TypeError, (error):
                log.error('Column %s has not specified joins validly:%s' % (mycolumn, error))

    def return_standard_filter(self,mycolumn,operation,value,loose_match=True):  
        col_type = mycolumn.type
        modeller = Modeller() 
        filter_func = modeller.return_function(col_type,operation,loose_match=True)   
        return lambda: filter_func(mycolumn.column,value)

    def pre_operations(self,column,operation,value,cls_ref=None,**kw):
        #First let's see if we have a column X operation specific filter
        #We will only need to use these filter by table column if the ones from Modeller are 
        #inadequate. 
        #If we are looking at the System class and column 'arch' with the 'is not' operation, it will try and get
        # System.arch_is_not_filter
        if cls_ref is None:          
            match_obj = re.search('^(.+)?Search$',self.__class__.__name__) 
            cls_ref = globals()[match_obj.group(1)]
            if cls_ref is None:
                raise BeakerException('No cls_ref passed in and class naming convention did give valid class')
        results_dict = {}
        underscored_operation = re.sub(' ','_',operation) 
        column_match = re.match('^(.+)?/(.+)?$',column)
        try:
            if column_match.group():
                #if We are searchong on a searchable_column that is something like 'System/Name' 
                #and the 'is not' operation, it will look for the SystemName_is_not_filter method
                column_mod = '%s%s' % (column_match.group(1).capitalize(),column_match.group(2).capitalize()) 
        except AttributeError, (error):
            column_mod = column.lower()
         
        col_op_filter = getattr(cls_ref,'%s_%s_filter' % (column_mod,underscored_operation),None)
        results_dict.update({'col_op_filter':col_op_filter})         
        #At this point we can also call a custom function before we try to append our results
        
        col_op_pre = getattr(cls_ref,'%s_%s_pre' % (column_mod,underscored_operation),None)           
        if col_op_pre is not None:
            results_dict.update({'results_from_pre': col_op_pre(value,col=column,op = operation, **kw)})  
        return results_dict 
         
    @classmethod 
    def search_on(cls,field,cls_ref=None): 
        """
        search_on() takes the field name we will search by, and
        returns the operations suitable for the field type it represents
        """
        if cls_ref is None:          
            match_obj = re.search('^(.+)?Search$',cls.__name__) 
            cls_ref = globals()[match_obj.group(1)]
            if cls_ref is None:
                raise BeakerException('No cls_ref passed in and class naming convention did give valid class')          
        try:
            field_type = cls_ref.get_field_type(field) 
            vals = None
            try:
                vals = cls_ref.search_values(field)
            except AttributeError:
                log.debug('Not using predefined search values for %s->%s' % (cls_ref.__name__,field))  
        except AttributeError, (error):
            log.error('Error accessing attribute within search_on: %s' % (error))
        else: 
            return dict(operators = cls_ref.search_operators(field_type), values=vals)

    @classmethod 
    def field_type(cls,field): 
       """ 
       Takes a field string (ie'Processor') and returns the type of the field
       """  
       match_obj = re.search('^(.+)?Search$',cls.__name__) 
       cls_ref = globals()[match_obj.group(1)]  
  
       field_type = cls_ref.get_field_type(field)  
       if field_type:
           return field_type
       else:
           log.debug('There was a problem in retrieving the field_type for the column %s' % field)
           return

    @classmethod
    def translate_class_to_name(cls, class_ref):
        """Translate the class ref into the text that is used in the 'Table' column"""
        if hasattr(class_ref, 'display_name'):
            return class_ref.display_name
        else:
            return class_ref.__name__

    @classmethod
    def translate_name_to_class(cls, display_name):
        """Translate the text in the 'Table' column to the internal class"""
        class_ref = None
        # First check if any SystemObject has a 'display_name'
        # attribute that matches, otherwise check against the class
        # name
        for system_object_class in SystemObject.__subclasses__():
            if hasattr(system_object_class, 'display_name') and \
                system_object_class.display_name == display_name:
                class_ref = system_object_class
                break
        if class_ref is None:
            for system_object_class in SystemObject.__subclasses__():
                if system_object_class.__name__ == display_name:
                    class_ref = system_object_class
                    break
        return class_ref

    @classmethod
    def split_class_field(cls,class_field):
        class_field_list = class_field.split('/')     
        display_name = class_field_list[0]
        field = class_field_list[1] 
        return (display_name,field)

    @classmethod
    def create_search_table(cls,*args,**kw): 
        cls_name = re.sub('Search','',cls.__name__)
        cls_ref = globals()[cls_name]  
        searchable = cls_ref.get_searchable(*args,**kw)
        searchable.sort()
        return searchable

    @classmethod
    def create_complete_search_table(cls, *args, **kw):
        searchable = cls.create_search_table(*args, **kw)
        table_options = {}
        for col in searchable:
            table_options[col] = cls.get_search_options(col)
        return table_options


class RecipeSearch(Search): pass

class JobSearch(Search):
    search_table = []

class TaskSearch(Search):
    search_table = []

class DistroSearch(Search):
    search_table = []

class DistroTreeSearch(Search): pass

class KeySearch(Search):
    search_table = []

    @classmethod 
    def get_search_options(cls, keyvalue_field, *args, **kw):
        return_dict = {}
        search = System.search.search_on_keyvalue(keyvalue_field)
        search.sort()
        return_dict['search_by'] = search
        return return_dict

class LabControllerActivitySearch(Search):
    search_table = []


class GroupActivitySearch(Search):
    search_table = []
    def __init__(self, activity):
        self.queri = activity


class SystemActivitySearch(Search):
    search_table = []
    def __init__(self, activity):
        self.queri = activity

class DistroTreeActivitySearch(Search):
    search_table = []

class DistroActivitySearch(Search):
    search_table = []


class ActivitySearch(Search):
    search_table = [] 

class HistorySearch(Search):
    search_table = []   

class SystemSearch(Search): 
    search_table = []
    column_table = [] 
    def __init__(self,systems=None):
        if systems:
            self.queri = systems.distinct()
        else:
            self.queri = session.query(model.System).distinct()
       
        self.system_columns_desc = []
        self.extra_columns_desc = []
  
    def __getitem__(self,key):
        pass
 
    def get_column_descriptions(self):
        return self.system_columns_desc

    def append_results(self,cls_ref,value,column,operation,**kw):
        """ 
        append_results() will take a value, column and operation from the search field,
        as well as the class of which the search pertains to, and will append the join
        and the filter needed to return the correct results.   
        """     
        #First let's see if we have a column X operation specific filter
        #We will only need to use these filter by table column if the ones from Modeller are 
        #inadequate. 
        #If we are looking at the System class and column 'arch' with the 'is not' operation, it will try and get
        # System.arch_is_not_filter
        value = value.strip()
        underscored_operation = re.sub(' ','_',operation)
        col_op_filter = getattr(cls_ref,'%s_%s_filter' % (column.lower(),underscored_operation),None)
         
        #At this point we can also call a custom function before we try to append our results
        
        col_op_pre = getattr(cls_ref,'%s_%s_pre' % (column.lower(),underscored_operation),None) 
                   
        if col_op_pre is not None:
            results_from_pre = col_op_pre(value,col=column,op = operation, **kw)
        else:
            results_from_pre = None
        mycolumn = cls_ref.create_column(column, results_from_pre)
        self.__do_join(cls_ref, mycolumn)
        modeller = Modeller()
        if col_op_filter:
            filter_func = col_op_filter
            filter_final = lambda: filter_func(mycolumn.column,value)
            #If you want to pass custom args to your custom filter, here is where you do it
            if kw.get('keyvalue'):
                filter_final = lambda: filter_func(mycolumn, value, key_name = kw['keyvalue'])
        else:
            #using just the regular filter operations from Modeller
            try:
                col_type = mycolumn.type
            except AttributeError, (error):
                log.error('Error accessing attribute type within append_results: %s' % (error))
            modeller = Modeller()
            filter_func = modeller.return_function(col_type,operation,loose_match=True)
            filter_final = lambda: filter_func(mycolumn.column,value)
        self.queri = self.queri.filter(filter_final())

    def _get_mapped_objects(self, tables):
        mapped_objects = []
        for table in tables:
            try:
                am_mapped_object = issubclass(table, model.MappedObject)
                if am_mapped_object:
                    mapped_objects.append(table)
            except TypeError: #We are possible a relation, which is an object
                pass
        return mapped_objects


    def __do_join(self, cls_ref, mycolumn):
        if mycolumn.relations:
            # This column has specified it needs a join, so let's add it to the all the joins
            # that are pertinent to this class. We do this so there is only one point where we add joins
            # to the query.

            # Sometimes the relations/table are backrefs which are not
            # populated until the sqla model initialisation code
            if callable(mycolumn.relations):
                mycolumn.relations = mycolumn.relations()
            onclause = getattr(mycolumn, 'onclause', None)
            if onclause is not None and callable(mycolumn.onclause):
                mycolumn.onclause = mycolumn.onclause()
            if isinstance(mycolumn, AliasedColumn):
                relations = mycolumn.relations
                # Make sure not to deal with Collections as we can't alias those
                tables_to_alias = self._get_mapped_objects(relations)
                aliased_table = map(lambda x: aliased(x), tables_to_alias)
                if len(aliased_table) > 1:
                    for at in aliased_table:
                        if get_alias_target(at) == mycolumn.target_table:
                            aliased_table_target = at
                else:
                    aliased_table_target = aliased_table[0]
                mycolumn.column = getattr(aliased_table_target, mycolumn.column_name)
                relations = set(tables_to_alias) ^ set(relations) # Get the difference
                # Recombine what was aliased and not
                if relations:
                    relations = list(relations) + aliased_table
                else:
                    relations = aliased_table
                mycolumn.relations = relations
            else:
                pass
            self.queri = mycolumn.column_join(self.queri)

    def add_columns_desc(self,result_columns):
        if result_columns is not None:
            for elem in result_columns:
                (display_name,col) = self.split_class_field(elem)
                cls_ref = self.translate_name_to_class(display_name)
                mycolumn = cls_ref.create_column(col)
                # If they are System columns we won't need to explicitly add
                # them to the query, as they are already returned in
                # the System query.
                self.system_columns_desc.append(elem)
                self.__do_join(cls_ref, mycolumn)
 
    def return_results(self): 
        return self.queri        

    @classmethod
    def create_complete_search_table(cls, *args, **kw):
        searchable = cls.create_search_table(*args, **kw)
        table_options = {}
        for col in searchable:
            #if you have any custom columns (i.e Key/Value, then get their results here)
            if col.lower() == 'key/value':
                table_options[col] = {'keyvals': KeyModel.get_all_keys()}
                expanded_keyvals = {}
                for k in table_options[col]['keyvals']:
                    expanded_keyvals.update({ k : Key.search.get_search_options(k) } )
                    #table_options[col]['keyvals'] = { k:Key.search.get_search_options(k) }
                table_options[col].update(expanded_keyvals)
                continue
            table_options[col] = cls.get_search_options(col)
        return table_options

    @classmethod
    def create_column_table(cls,options): 
        return cls._create_table(options,cls.column_table)        

    @classmethod
    def create_search_table(cls,options): 
        return cls._create_table(options,cls.search_table) 
   
    @classmethod
    def _create_table(cls,options,lookup_table):  
        """
        create_table will set and return the class' attribute with
        a list of searchable 'combinations'.
        These 'combinations' merely represent a table and a column.
        An example of a table entry may be 'CPU/Vendor' or 'System/Name'
        """
        #Clear the table if it's already been created
        if lookup_table != None:
           lookup_table = []       
        for i in options:
            for class_ref ,v in i.iteritems():
                display_name = cls.translate_class_to_name(class_ref)
                for rule,v1 in v.iteritems():  
                    searchable = class_ref.get_searchable()
                    if rule == 'all':
                        for item in searchable: 
                            lookup_table.append('%s/%s' % (display_name,item))  
                    if rule == 'exclude': 
                        for item in searchable: 
                            if v1.count(item) < 1:
                                lookup_table.append('%s/%s' % (display_name,item))  
                    if rule == 'include':
                        for item in searchable:
                            if v1.count(item) > 1:
                                 lookup_table.append('%s/%s' % (display_name,item))  

        lookup_table.sort()
        return lookup_table

    @classmethod 
    def field_type(cls,class_field): 
       """ 
       Takes a class/field string (ie'CPU/Processor') and returns the type of the field
       """
       returned_class_field = cls.split_class_field(class_field) 
       display_name = returned_class_field[0]
       field = returned_class_field[1]        
      
       class_ref = cls.translate_name_to_class(display_name)
       field_type = class_ref.get_field_type(field)  
       
       if field_type:
           return field_type
       else:
           log.debug('There was a problem in retrieving the field_type for the column %s' % field)
           return

    @classmethod
    def search_on_keyvalue(cls,key_name):
        """   
        search_on_keyvalue() takes a key_name and returns the operations suitable for the 
        field type it represents
        """
        row = model.Key.by_name(key_name) 
        if row.numeric == 1:
            field_type = 'Numeric'
        elif row.numeric == 0:
            field_type = 'String'        
        else:
            log.error('Cannot determine type for %s, defaulting to generic' % key_name)
            field_type = 'generic'

        return Key.search_operators(field_type,loose_match=True)
        
             
    @classmethod 
    def search_on(cls,class_field): 
        """
        search_on() takes a combination of class name and field name (i.e 'Cpu/vendor') and
        returns the operations suitable for the field type it represents
        """ 
        returned_class_field = cls.split_class_field(class_field) 
        display_name = returned_class_field[0]
        field = returned_class_field[1]        
        class_ref = cls.translate_name_to_class(display_name)
        
        try:
            field_type = class_ref.get_field_type(field) 
            vals = None
            try:
                vals = class_ref.search_values(field)
            except AttributeError:
                log.debug('Not using predefined search values for %s->%s' % (class_ref.__name__,field))
        except AttributeError, (error):
            log.error('Error accessing attribute within search_on: %s' % (error))
        else:
            return dict(operators = class_ref.search_operators(field_type), values = vals)

class SystemObject(object):

    # Defined on subclasses
    searchable_columns = {}
    search_values_dict = {}

    @classmethod
    def create_column(cls, column, *args, **kw):
        column = cls.searchable_columns.get(column)
        # AliasedColumn will be modified, so make sure
        # we do not pass the same object around.
        if isinstance(column, AliasedColumn):
            column = copy(column)
        return column

    @classmethod
    def get_field_type(cls,field):
        mycolumn = cls.searchable_columns.get(field)
        if mycolumn:
            try:
                field_type = mycolumn.type 
                return field_type
            except AttributeError, (error):
                log.error('No type specified for %s in searchable_columns:%s' % (field,error))
        else:
            log.error('Column %s is not a mapped column nor is it part of searchable_columns' % field)
                    
    @classmethod
    def search_values(cls,col):  
       if cls.search_values_dict.has_key(col):
           return cls.search_values_dict[col]()
       
    @classmethod
    def get_searchable(cls,*args,**kw):
        """
        get_searchable will return the description of how the calling class can be searched by returning a list
        of fields that can be searched after any field filtering has
        been applied
        """
        searchable_columns = [k for (k,v) in cls.searchable_columns.iteritems()
                if v is None or not v.hidden]
        if 'exclude' in kw:
            if type(kw['without']) == type(()):
                for i in kw['exclude']:
                    try:
                        del searchable_columns[i]
                    except KeyError,e:
                        log.error('Cannot remove column %s from searchable column in class %s as it is not a searchable column in the first place' % (i,cls.__name__))
        return searchable_columns

    @classmethod
    def search_operators(cls,field):
        """
        search_operators returns a list of the different types of searches that can be done on a given field.
        It relies on the Modeller class, which stores these relationships.
        """             
        m = Modeller() 
    
        try: 
            return m.return_operators(field)
        except KeyError, (e): 
            log.error('Failed to find operators for field %s, got error: %s' % (field,e))


class System(SystemObject): 
    search = SystemSearch
    search_table = []
    searchable_columns = {'Vendor'    : MyColumn(column=model.System.vendor,col_type='string'),
                          'Name'      : MyColumn(column=model.System.fqdn,col_type='string'),
                          'Lender'    : MyColumn(column=model.System.lender,col_type='string'),
                          'Location'  : MyColumn(column=model.System.location, col_type='string'),
                          'Added'     : MyColumn(column=model.System.date_added, col_type='date'),
                          'LastInventoried': MyColumn(column=model.System.date_lastcheckin,
                                             col_type='date'),
                          'Model'     : MyColumn(column=model.System.model,col_type='string'),
                          'SerialNumber': MyColumn(column=model.System.serial, col_type='string'),
                          'Memory'    : MyColumn(column=model.System.memory,col_type='numeric'),
                          'Hypervisor': MyColumn(column=model.Hypervisor.hypervisor, col_type='string', relations='hypervisor'),
                          'NumaNodes' : MyColumn(column=model.Numa.nodes, col_type='numeric', relations='numa'),
                          'Notes'     : AliasedColumn(column_name='text',
                                            col_type='string', relations=[model.Note],
                                            onclause=model.System.notes),
                          'User'      : AliasedColumn(column_name='user_name',
                                            relations=[model.User],
                                            col_type='string',
                                            onclause=model.System.user),
                          'Owner'     : AliasedColumn(column_name='user_name',
                                            col_type='string', relations=[model.User],
                                            onclause=model.System.owner),
                          'Status'    : MyColumn(column=model.System.status, col_type='string'),
                          'Arch'      : MyColumn(column=model.Arch.arch,
                                            col_type='string',
                                            relations=[model.System.arch],
                                            eagerload=False,),
                          'Type'      : MyColumn(column=model.System.type, col_type='string'),
                          'Reserved'  : MyColumn(column=model.Reservation.start_time, col_type='date', relations='open_reservation'),
                          'PowerType' : MyColumn(column=model.PowerType.name, col_type='string',
                                            relations=[model.System.power, model.Power.power_type]),
                          'LoanedTo'  : AliasedColumn(column_name='user_name',
                                            col_type='string',
                                            onclause=model.System.loaned,
                                            relations=[model.User]),
                          'LoanComment': MyColumn(
                                            column=model.System.loan_comment,
                                            col_type='string'),
                          'Group'       : AliasedColumn(col_type='string',
                                                        column_name='name',
                                                        eagerload=False,
                                                        onclause=model.System.pools,
                                                        relations=[model.SystemPool],
                                                        hidden=True),
                          'Pools'       : AliasedColumn(col_type='string',
                                                        column_name='name',
                                                        eagerload=False,
                                                        onclause=model.System.pools,
                                                        relations=[model.SystemPool]),
                          'LabController' : AliasedColumn(column_name='fqdn',
                                            col_type='string', relations=[model.LabController],
                                            onclause=model.System.lab_controller),
                         }
    search_values_dict = {'Status'    : lambda: [status for status in 
                                                 model.SystemStatus.values() if status != 'Removed'],
                          'Type'      : lambda: model.SystemType.values(),
                          'Hypervisor': lambda: [''] + model.Hypervisor.get_all_names(),
                         }
    @classmethod
    def filter_by_exact_date_for_datetime(cls, col, date_string):
        """Filters using a given date on datetime columns"""
        if not date_string:
            return col == None
        else:
            date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
            return and_(col >= date, col < date + datetime.timedelta(days=1))
    added_is_filter = filter_by_exact_date_for_datetime
    reserved_is_filter = filter_by_exact_date_for_datetime
    lastinventoried_is_filter = filter_by_exact_date_for_datetime

    @classmethod
    def filter_by_future_date_for_datetime(cls, col, date_string):
        if not date_string:
            return col == None
        else:
            date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
            return col >= date + datetime.timedelta(days=1)
    added_after_filter = filter_by_future_date_for_datetime
    reserved_after_filter = filter_by_future_date_for_datetime
    lastinventoried_after_filter = filter_by_future_date_for_datetime

    @classmethod
    def filter_by_past_date_for_datetime(cls, col, date_string):
        if not date_string:
            return col == None
        else:
            date = datetime.datetime.strptime(date_string, '%Y-%m-%d')
            return col < date
    added_before_filter = filter_by_past_date_for_datetime
    reserved_before_filter = filter_by_past_date_for_datetime
    lastinventoried_before_filter = filter_by_past_date_for_datetime

    @classmethod
    def arch_is_not_filter(cls,col,val):
        """
        arch_is_not_filter is a function dynamically called from append_results.
        It serves to provide a table column operation specific method of filtering results of System/Arch
        """       
        if not val: 
           return or_(col != None, col != val) 
        else:
            #If anyone knows of a better way to do this, by all means...
            query = model.System.query.filter(model.System.arch.any(model.Arch.arch == val))
          
        ids = [r.id for r in query]  
        return not_(model.System.id.in_(ids))

    @classmethod
    def notes_contains_filter(cls, col, val, **kw):
        """
        notes_contains_filter is a function dynamically called from append_results.
        It serves to provide a table column operation specific method of filtering results of System/Notes

        In this case it specifically searches case-insensitively through System/Notes
        """
        query = model.System.query.filter(model.System.notes.any(model.Note.text.ilike(val)))
        return model.System.id.in_([x.id for x in query])

class Recipe(SystemObject):
    search = RecipeSearch
    searchable_columns = {
                            'Id' : MyColumn(col_type='numeric', column=model.MachineRecipe.id),
                            'Whiteboard' : MyColumn(col_type='string', column=model.Recipe.whiteboard),
                            'System' : MyColumn(col_type='string', column=model.RecipeResource.fqdn,
                                relations=[model.Recipe.resource]),
                            'Arch' : MyColumn(col_type='string', column=model.Arch.arch,
                                relations=[model.Recipe.distro_tree, model.DistroTree.arch]),
                            'Distro' : MyColumn(col_type='string', column=model.Distro.name,
                                relations=[model.Recipe.distro_tree, model.DistroTree.distro]),
                            'Status' : MyColumn(col_type='string', column=model.Recipe.status),
                            'Result' : MyColumn(col_type='string', column=model.Recipe.result),
                         }

    search_values_dict = {'Status' : lambda: model.TaskStatus.values(),
                          'Result' : lambda: model.TaskResult.values()}
    

class Distro(SystemObject):
    search = DistroSearch
    searchable_columns = {'Name' : MyColumn(col_type='string', column=model.Distro.name),
        'OSMajor' : MyColumn(col_type='string', column=model.OSMajor.osmajor,
            relations=[model.Distro.osversion, model.OSVersion.osmajor]),
        'OSMinor' : MyColumn(col_type='string', column=model.OSVersion.osminor,
            relations=[model.Distro.osversion]),
        'Created' : MyColumn(col_type='date', column=model.Distro.date_created),
        'Tag' : MyColumn(col_type='string', column=model.DistroTag.tag,
            relations=[model.Distro._tags])
                         }
    search_values_dict = {'Tag' : lambda: [e.tag for e in model.DistroTag.list_by_tag(u'')]}

    @classmethod
    def tag_is_not_filter(cls,col,val):
        """
        tag_is_not_filter is a function dynamically called from append_results.
        """
        return not_(model.Distro._tags.any(model.DistroTag.tag == val))

class DistroTree(SystemObject):
    search = DistroTreeSearch
    searchable_columns = {
        'Name':    MyColumn(col_type='string', column=model.Distro.name, relations='distro'),
        'Variant': MyColumn(col_type='string', column=model.DistroTree.variant),
        'Arch':    MyColumn(col_type='string', column=model.Arch.arch, relations='arch'),
        'OSMajor': MyColumn(col_type='string', column=model.OSMajor.osmajor,
                            relations=['distro', 'osversion', 'osmajor']),
        'OSMinor' : MyColumn(col_type='string', column=model.OSVersion.osminor,
            relations=[model.Distro.osversion]),
        'Created' : MyColumn(col_type='date', column=model.DistroTree.date_created),
        'Tag':     MyColumn(col_type='string', column=model.DistroTag.tag,
                            relations=['distro', '_tags']),
    }
    search_values_dict = {
        'Arch':    lambda: [unicode(arch) for arch in model.Arch.query.order_by(model.Arch.arch)],
        'Tag':     lambda: [unicode(tag) for tag in model.DistroTag.query.order_by(model.DistroTag.tag)],
    }

    tag_is_not_filter = Distro.tag_is_not_filter


class Activity(SystemObject):
    search = ActivitySearch    
    searchable_columns = { 
                           'User' : MyColumn(col_type='string', column=model.User.user_name, relations='user'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value),
                         }  


class LabControllerActivity(SystemObject):
    search = LabControllerActivitySearch
    searchable_columns = { 'LabController/Name' : MyColumn(col_type='string', column=model.LabController.fqdn, relations='object'),
                           'User' : MyColumn(col_type='string', column=model.User.user_name, relations='user'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value), }


class SystemActivity(SystemObject):
    search = SystemActivitySearch
    searchable_columns = {
                           'System/Name' : MyColumn(col_type='string', column=model.System.fqdn, relations='object'),
                           'User' : MyColumn(col_type='string', column=model.User.user_name, relations='user'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value),
                         }


class GroupActivity(SystemObject):
    search = GroupActivitySearch
    searchable_columns = {
                           'Group/Name' : MyColumn(col_type='string', column=model.Group.display_name, relations='object'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value),
                         }

class DistroTreeActivity(SystemObject):
    search = DistroTreeActivitySearch
    searchable_columns = {'DistroTree/Arch': MyColumn(col_type='string',
                                                  column=model.Arch.arch,
                                                  relations=['object', 'arch'],
                                                  aliased=False),
                          'DistroTree/Variant': MyColumn(col_type='string',
                                                    column=model.DistroTree.variant,
                                                    relations='object',
                                                    aliased=False),
                          'DistroTree/Distro Name': MyColumn(col_type='string',
                                                        column=model.Distro.name,
                                                        relations=['object',
                                                                   'distro'],
                                                        aliased=False),
                          'Via': MyColumn(col_type='string',
                                     column=model.Activity.service),
                          'Property': MyColumn(col_type='string',
                                          column=model.Activity.field_name),
                          'Action': MyColumn(col_type='string',
                                        column=model.Activity.action),
                          'Old Value': MyColumn(col_type='string',
                                           column=model.Activity.old_value),
                          'New Value': MyColumn(col_type='string',
                                           column=model.Activity.new_value),}


class DistroActivity(SystemObject):
    search = DistroActivitySearch
    searchable_columns = {
                           'Distro/Name' : MyColumn(col_type='string', column=model.Distro.name, relations='object'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value),
                         }


class History(SystemObject):
    search = HistorySearch
    searchable_columns = {
                          'User' : MyColumn(col_type='string', column=model.User.user_name,relations='user'),
                          'Service' : MyColumn(col_type='string', column=model.Activity.service),
                          'Field Name' : MyColumn(col_type='string', column=model.Activity.field_name),
                          'Action' : MyColumn(col_type='string', column=model.Activity.action),
                          'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                          'New Value' : MyColumn(col_type='string', column=model.Activity.new_value) 
                         }  


class Key(SystemObject):
    searchable_columns = {'Value': None}
    search = KeySearch

    @classmethod
    def create_column(cls, column, type):
        if column == 'Value':
            return KeyCreator.create(type=type)
        else:
            raise ValueError('%s is an unrecognised column', column)

    @classmethod
    def search_operators(cls,type,loose_match=None):
        m = Modeller()
        operators = m.return_operators(type,loose_match)
        return operators

    @classmethod
    def value_pre(cls,value,**kw): 
        if not kw.get('keyvalue'):
            raise Exception, 'value_pre needs a keyvalue. keyvalue not found' 
        result = model.Key.by_name(kw['keyvalue']) 
        int_table = result.numeric
        key_id = result.id
        if int_table == 1:
            return KeyCreator.INT
        elif int_table == 0:
            return KeyCreator.STRING
        else:
            log.error('Unexpected result %s from value_pre in class %s' % (int_table,cls.__name__))

    @classmethod
    def value_is_pre(cls,value,**kw): 
       return cls.value_pre(value,**kw)

    @classmethod
    def value_is_not_pre(cls,value,**kw):
        return cls.value_pre(value,**kw)
 
    @classmethod
    def value_less_than_pre(cls,value,**kw):
        return cls.value_pre(value,**kw)

    @classmethod
    def value_greater_than_pre(cls,value,**kw):
        return cls.value_pre(value,**kw)
    
    @classmethod
    def value_contains_pre(cls,value,**kw):
        return cls.value_pre(value,**kw)

    @classmethod
    def value_less_than_filter(cls, col, val, key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
        return and_(col.column < val, col.parent_entity.key_id == key_id)

    @classmethod
    def value_greater_than_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
        return and_(col.column > val, col.parent_entity.key_id == key_id)

    @classmethod
    def value_contains_filter(cls, col, val, key_name):
        result = model.Key.by_name(key_name) 
        key_id = result.id
        return and_(col.column.like('%%%s%%' % val), col.parent_entity.key_id == key_id)
        
    @classmethod
    def value_is_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
        column_parent = col.parent_entity
        if not val:
            return and_(or_(col.column == val, col.column == None),
                or_(column_parent.key_id == key_id,
                column_parent.key_id == None))
        else:
            return and_(col.column == val, column_parent.key_id == key_id)

    @classmethod
    def value_is_not_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
        column_parent = col.parent_entity
        if int_table == 1:
            if not val:
                return and_(or_(col.column != val, col.column == None),
                    or_(column_parent.key_id == key_id, column_parent.key_id == None))
            else:
                return not_(model.System.key_values_int.any(
                    and_(model.Key_Value_Int.key_value==val,
                    model.Key_Value_Int.key_id==key_id)))
        elif int_table == 0:
            if not val:
                return and_(or_(col.column != val, column_parent.key_value == None),
                    or_(column_parent.key_id == key_id,
                    column_parent.key_id == None))
            else:
                return not_(model.System.key_values_string.any(
                    and_(model.Key_Value_String.key_value==val,
                    model.Key_Value_String.key_id==key_id)))


class Job(SystemObject):
    search = JobSearch
    display_name='Job'
    searchable_columns = {
                           'Id' : MyColumn(col_type='numeric',column=model.Job.id),
                           'Owner/Username' : MyColumn(col_type='string',column=model.User.user_name, relations='owner'),
                           'Owner/Email' : MyColumn(col_type='string',column=model.User.email_address, relations='owner'),
                           'Group': MyColumn(col_type='string',
                                             column=model.Group.group_name,
                                             relations='group'),
                           'Product': MyColumn(col_type='string', 
                                               column=model.Product.name, 
                                               relations=model.Job.product),
                           'Tag': MyColumn(col_type='string', 
                                           column=model.RetentionTag.tag,
                                           relations=model.Job.retention_tag),
                           'Status' : MyColumn(col_type='string', column=model.Job.status),
                           'Result' : MyColumn(col_type='string', column=model.Job.result),
                           'Whiteboard' : MyColumn(col_type='string', column=model.Job.whiteboard)
                         }

    search_values_dict = {'Status' : lambda: model.TaskStatus.values(),
                          'Result' : lambda: model.TaskResult.values(),
                          'Tag': lambda: [tag[0] for tag in 
                              model.RetentionTag.query.values(model.RetentionTag.tag)],
                          'Product': lambda: [('','None')] + ([p[0] for p in 
                              model.Product.query.values(model.Product.name)]) }

class Cpu(SystemObject):      
    display_name = 'CPU'   
    search_values_dict = { 'Hyper' : lambda: ['True','False'] }
    searchable_columns = {
                          'Vendor'      : CpuColumn(col_type='string',
                                              column = model.Cpu.vendor),
                          'Processors'  : CpuColumn(col_type='numeric',
                                              column = model.Cpu.processors),
                          'Hyper'       : CpuColumn(col_type='boolean',
                                              column = model.Cpu.hyper),
                          'Cores'       : CpuColumn(col_type='numeric',
                                              column = model.Cpu.cores),
                          'Sockets'     : CpuColumn(col_type='numeric',
                                              column = model.Cpu.sockets),
                          'Model'       : CpuColumn(col_type='numeric',
                                              column = model.Cpu.model),
                          'ModelName'   : CpuColumn(col_type='string',
                                              column = model.Cpu.model_name),
                          'Family'      : CpuColumn(col_type='numeric',
                                              column = model.Cpu.family),
                          'Stepping'    : CpuColumn(col_type='numeric',
                                              column = model.Cpu.stepping),
                          'Speed'       : CpuColumn(col_type='numeric',
                                              column = model.Cpu.speed),
                          'Flags'       : AliasedColumn(col_type='string',
                                              eagerload=False,
                                              target_table=[model.CpuFlag],
                                              column_name = 'flag',
                                              relations= lambda: [model.System.cpu, model.CpuFlag])
                         }

    @classmethod
    def flags_is_not_filter(cls,col,val,**kw):
        """
        flags_is_not_filter is a function dynamically called from append_results.
        It serves to provide a table column operation specific method of filtering results of CPU/Flags
        """       
        if not val:
            return col != val
        else:
            query = model.Cpu.query.filter(model.Cpu.flags.any(model.CpuFlag.flag == val))
            ids = [r.id for r in query]
            return or_(not_(model.Cpu.id.in_(ids)), col == None)
         
class Device(SystemObject):
    display_name = 'Devices'
    searchable_columns = {'Description' : DeviceColumn(col_type='string', column=model.Device.description),
                          'Vendor_id' : DeviceColumn(col_type='string', column=model.Device.vendor_id),
                          'Device_id' : DeviceColumn(col_type='string', column=model.Device.device_id),
                          'Driver' : DeviceColumn(col_type='string', column=model.Device.driver),
                          'Subsys_device_id' : DeviceColumn(col_type='string', column=model.Device.subsys_device_id),
                          'Subsys_vendor_id' : DeviceColumn(col_type='string', column=model.Device.subsys_vendor_id),}
      
    @classmethod
    def driver_is_not_filter(cls,col,val):
        if not val:
            return or_(col != None, col != val)
        else:
            query = model.System.query.filter(model.System.devices.any(model.Device.driver == val))
    
        ids = [r.id for r in query]  
        return not_(model.System.id.in_(ids))

class Disk(SystemObject):
    display_name = 'Disk'
    searchable_columns = {
        'Model': DiskColumn(col_type='string', column=model.Disk.model),
        'Size': DiskColumn(col_type='numeric', column=model.Disk.size),
        'SectorSize': DiskColumn(col_type='numeric', column=model.Disk.sector_size),
        'PhysicalSectorSize': DiskColumn(col_type='numeric',
            column=model.Disk.phys_sector_size),
    }

    # This is the special case for "is not" which is applied on 
    # one-to-many related entities...
    @classmethod
    def _is_not_filter(cls, col, val):
        if not val:
            return or_(col != None, col != val)
        return not_(model.System.disks.any(col == val))
    model_is_not_filter = _is_not_filter
    size_is_not_filter = _is_not_filter
    sectorsize_is_not_filter = _is_not_filter
    physicalsectorsize_is_not_filter = _is_not_filter
