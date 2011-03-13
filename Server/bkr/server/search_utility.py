import model
import re
import random
import sqlalchemy
from turbogears import flash, identity
from sqlalchemy import or_, and_, not_
from sqlalchemy.sql import visitors, select
from turbogears.database import session
from bkr.server.model import Key as KeyModel
import logging
log = logging.getLogger(__name__)

class MyColumn(object):
    """
    MyColumn is a class to hold information about a mapped column, 
    such as the actual mapped column, the type, and a relation it may
    have to another mapped object

    It should be overridden by classes that will consistently use a 
    relation to another mapped object.
    """
    def __init__(self,relations=None,col_type=None,column = None,has_alias=False):        
        if type(col_type) != type(''):
            raise TypeError('col_type var passed to %s must be string' % self.__class__.__name__)
        
        if relations is not None:
            if type(relations) != type([]) and type(relations) != type(''):
                raise TypeError('relation var passed to %s must be of type list of string' % self.__class__.__name__)
        self._has_alias = has_alias
        self._column = column
        self._type = col_type
        self._relations = relations
        
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
    def has_alias(self):
        return self._has_alias
    
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
    
class KeyColumn(MyColumn):
    """
    KeyColumn defines a relationship to system for either a string or int 
    type key
    """
    def __init__(self,**kw):
        try:
            if type(kw['relations']) != type([]):
                raise TypeError('relations var passed to MyColumn must be a list')
        except KeyError, (error):
            log.error('No relations passed to KeyColumn')
        else:  
            self._column = None 
            if not kw.get('int_column'):      
                self._int_column = model.key_value_int_table.c.key_value
            if not kw.get('string_column'):
                self._string_column = model.key_value_string_table.c.key_value
                
            self._type = None
            self._relations = kw['relations']
            super(KeyColumn,self).__init__(col_type = '',**kw) #Fudging col_type as we've already got our int/string col  
            
    @property
    def int_column(self):
        return self._int_column
    
    @property
    def string_column(self):
        return self._string_column
    
    def set_column(self,val):
        self._column = val
        
    def set_type(self,val):
        self._type = val
        
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
        
class Search:

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
                if type(relations) == type(''):
                    self.queri = self.queri.outerjoin(relations,aliased=True)    
                else:
                    for relation in relations:
                        if type(relation) == type([]):
                            self.queri = self.queri.outerjoin(relation,aliased=True) 
                        else:
                            self.queri = self.queri.outerjoin(relations,aliased=True)
                            break
            except TypeError, (error):
                log.error('Column %s has not specified joins validly:%s' % (column, error))                                                               

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
    def translate_name(cls,display_name):
        """ 
        translate_name() get's a reference to the class from it's display name 
        """
        try:
            class_ref = cls.class_external_mapping[display_name]
        except KeyError:
            log.error('Class %s does not have a mapping to display_name %s' % (cls.__name__,display_name))
            raise
        else:
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


class RecipeSearch(Search):
    def __init__(self,recipe):
        self.queri = recipe

class JobSearch(Search):
    search_table = []
    def __init__(self,job):
        self.queri = job

class TaskSearch(Search):
    search_table = []
    def __init__(self,task):
        self.queri = task

class DistroSearch(Search):
    search_table = []
    def __init__(self,distro):
        self.queri = distro

class KeySearch(Search):
    search_table = []

    @classmethod 
    def get_search_options(cls, keyvalue_field, *args, **kw):
        return_dict = {}
        search = System.search.search_on_keyvalue(keyvalue_field)
        search.sort()
        return_dict['search_by'] = search
        return return_dict

class SystemReserveSearch(Search):
    search_table = []
    def __init__(self,system_reserve=None):
        self.queri = system_reserve

class ActivitySearch(Search):
    search_table = [] 
    def __init__(self,activity):
        self.queri = activity
    
class HistorySearch(Search):
    search_table = []   
    def __init__(self,activity):
        self.queri = activity 
   
class SystemSearch(Search): 
    class_external_mapping = {}
    search_table = []
    column_table = [] 
    def __init__(self,systems=None):
        if systems:
            self.queri = systems
        else:
            self.queri = session.query(model.System)
       
        self.system_columns_desc = []
        self.extra_columns_desc = []
  
    def __getitem__(self,key):
        pass
 
    def get_column_descriptions(self):
        return [self.system_columns_desc,self.extra_columns_desc]

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
        underscored_operation = re.sub(' ','_',operation)
        col_op_filter = getattr(cls_ref,'%s_%s_filter' % (column.lower(),underscored_operation),None)
         
        #At this point we can also call a custom function before we try to append our results
        
        col_op_pre = getattr(cls_ref,'%s_%s_pre' % (column.lower(),underscored_operation),None) 
                   
        if col_op_pre is not None:
            results_from_pre = col_op_pre(value,col=column,op = operation, **kw)
        else:
            results_from_pre = None
        
        mycolumn = cls_ref.searchable_columns.get(column)  
        if mycolumn:
            try: 
                self.__do_join(cls_ref,mycolumn=mycolumn,results_from_pre = results_from_pre)             
            except TypeError, (error):
                log.error(error)
        else:       
            log.error('Error accessing attribute within append_results')
        
        modeller = Modeller()          
        if col_op_filter:
            filter_func = col_op_filter   
            filter_final = lambda: filter_func(mycolumn.column,value)
            #If you want to pass custom args to your custom filter, here is where you do it
            if kw.get('keyvalue'): 
                filter_final = lambda: filter_func(mycolumn.column,value,key_name = kw['keyvalue'])   
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


    def __do_join(self,cls_ref,col_name=None,mycolumn=None,results_from_pre=None,id=None): 
            if not mycolumn and not col_name:
                raise ValueError('Need to specify either a myColumn type or column name') 
            if not mycolumn:
                 mycolumn = cls_ref.searchable_columns.get(col_name)   
                 if not mycolumn:
                     log.error('Error accessing column %s in class %s' % (col_name,cls_ref.__name__))  
             
            if cls_ref is Key:    
                if results_from_pre == 'string':
                    mycolumn.set_column(mycolumn.string_column)
                    mycolumn.set_type('string')
                elif results_from_pre == 'int':
                    mycolumn.set_column(mycolumn.int_column)
                    mycolumn.set_type('int')
                else:
                    log.error('Expecting the string value \'string\' or \'int\' to be returned from col_op_pre function when searching on Key/Value');       
            if mycolumn.relations: 
                #This column has specified it needs a join, so let's add it to the all the joins
                #that are pertinent to this class. We do this so there is only one point where we add joins 
                #to the query
                #cls_ref.joins.add_join(col_string = str(column),join=mycolumn.join)
                system_relations = mycolumn.relations
                is_alias = mycolumn.has_alias
                if type(system_relations) == type(''):
                    if id is not None:
                        self.queri = self.queri.outerjoin(system_relations,aliased=is_alias,id=id)    
                    self.queri = self.queri.outerjoin(system_relations,aliased=is_alias)    
                else:    
                    for relations in system_relations:
                        if type(relations) == type([]):
                            if id is not None: 
  				self.queri = self.queri.outerjoin(relations,aliased=is_alias,id=id)    
                            self.queri = self.queri.outerjoin(relations,aliased=False)    
                        else:
                            if id is not None: 
                                self.queri = self.queri.outerjoin(system_relations,aliased=is_alias,id=id)
                            self.queri = self.queri.outerjoin(system_relations,aliased=is_alias)
                            break     
                         
    def add_columns_desc(self,result_columns): 
        if result_columns is not None:
            for elem in result_columns: 
                (display_name,col) = self.split_class_field(elem) 
                cls_ref = self.translate_name(display_name)  
                col_ref = cls_ref.searchable_columns[col].column
                #If they are System columns we won't need to explicitly add them to the query, as they are already returned in the System query  
                if cls_ref is System:     
                    self.system_columns_desc.append(elem)
                elif col_ref is not None: 
                    self.extra_columns_desc.append(elem)
                    self.adding_columns = True 
                    rand_id = random.random()
                    self.__do_join(cls_ref,col_name=col,id=rand_id)
                    self.queri = self.queri.add_column(col_ref,id=rand_id)         
 
    def return_results(self): 
        return self.queri        

    @classmethod
    def create_complete_search_table(cls, *args, **kw):
        searchable = cls.create_search_table(*args, **kw)
        table_options = {}
        for col in searchable:
            #if you have any custom columns (i.e Key/Value, then get their results here)
            if col.lower() == 'key/value':
                #HACK to remove MODULE from Key/Value search. This is also implemented in
                # get_value_search_options() to cater for an Ajax call
                table_options[col] ={'keyvals' :  [x for x in KeyModel.get_all_keys() if x != 'MODULE']}
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
            for obj,v in i.iteritems():
                display_name = cls.create_mapping(obj)
                for rule,v1 in v.iteritems():  
                    searchable = obj.get_searchable()
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
    def create_mapping(cls,obj):
        display_name = getattr(obj,'display_name',None)
        if display_name != None:
            display_name = obj.display_name
                  
            #If the display name is already mapped to this class
            if cls.class_external_mapping.has_key(display_name) and cls.class_external_mapping.get(display_name) is obj: 
                #this class is already mapped, all good
                pass 
            elif cls.class_external_mapping.has_key(display_name) and cls.class_external_mapping.get(display_name) is not obj:                   
                log.debug("Display name %s is already in use. Will try and use %s as display name for class %s" % (display_name, obj.__name__,obj.__name__))
                display_name = obj.__name__             
        else:
            display_name = obj.__name__
              
        #We have our final display name, if it still exists in the mapping
        #there isn't much we can do, and we don't want to overwrite it. 
        if cls.class_external_mapping.has_key(display_name) and cls.class_external_mapping.get(display_name) is not obj: 
            log.error("Display name %s cannot be set for %s" % (display_name,obj.__name__))               
        else: 
            cls.class_external_mapping[display_name] = obj
        return display_name

    @classmethod 
    def field_type(cls,class_field): 
       """ 
       Takes a class/field string (ie'CPU/Processor') and returns the type of the field
       """
       returned_class_field = cls.split_class_field(class_field) 
       display_name = returned_class_field[0]
       field = returned_class_field[1]        
      
       class_ref = cls.translate_name(display_name)
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
        class_ref = cls.translate_name(display_name)
        
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

class SystemObject:
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
        try:           
            searchable_columns = [k for (k,v) in cls.searchable_columns.iteritems()]
            if 'exclude' in kw:
                if type(kw['without']) == type(()):
                    for i in kw['exclude']:
                        try:
                            del searchable_columns[i]
                        except KeyError,e:
                            log.error('Cannot remove column %s from searchable column in class %s as it is not a searchable column in the first place' % (i,cls.__name__))
            return searchable_columns
        except AttributeError,(e):
            log.debug('Unable to access searchable_columns of class %s' % cls.__name__)
            return []
    
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
            log.error('Failed to find search_type by index %s, got error: %s' % (index_type,e))
            
class System(SystemObject): 
    search = SystemSearch
    search_table = []
    searchable_columns = {'Vendor'    : MyColumn(column=model.System.vendor,col_type='string'),
                          'Name'      : MyColumn(column=model.System.fqdn,col_type='string'),
                          'Lender'    : MyColumn(column=model.System.lender,col_type='string'),
                          'Location'  : MyColumn(column=model.System.location, col_type='string'),
                          'Added'     : MyColumn(column=model.System.date_added, col_type='date'),
                          'Model'     : MyColumn(column=model.System.model,col_type='string'),
                          'Memory'    : MyColumn(column=model.System.memory,col_type='numeric'),
                          'NumaNodes' : MyColumn(column=model.Numa.nodes, col_type='numeric', relations='numa'),
                          'User'      : MyColumn(column=model.User.user_name, col_type='string',has_alias=True, relations='user'),
                          'Owner'     : MyColumn(column=model.User.user_name, col_type='string',has_alias=True, relations='owner'),
                          'Status'    : MyColumn(column=model.SystemStatus.status, col_type='string', relations='status'),
                          'Arch'      : MyColumn(column=model.Arch.arch, col_type='string', relations='arch'),
                          'Type'      : MyColumn(column=model.SystemType.type, col_type='string', relations='type'),
                          'PowerType' : MyColumn(column=model.PowerType.name, col_type='string', relations=['power','power_type']),
                          'LoanedTo'  : MyColumn(column=model.User.user_name,col_type='string',has_alias=True, relations='loaned'),
                          'Group'     : MyColumn(column=model.Group.group_name, col_type='string',has_alias=True, relations ='groups')
                         }  
    search_values_dict = {'Status' : lambda: model.SystemStatus.get_all_status_name(),
                          'Type' : lambda: model.SystemType.get_all_type_names() }   
    @classmethod
    def added_is_filter(cls,col,val):
        if not val:
            return col == None
        else:
            return and_(col >= '%s 00:00:00' % val, col <= '%s 23:59:99' % val)

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
            query = model.System.query().filter(model.System.arch.any(model.Arch.arch == val))       
          
        ids = [r.id for r in query]  
        return not_(model.system_table.c.id.in_(ids)) 

class Recipe(SystemObject):
    search = RecipeSearch
    searchable_columns = {
                            'Id' : MyColumn(col_type='numeric', column=model.Recipe.id),
                            'Whiteboard' : MyColumn(col_type='string', column=model.Recipe.whiteboard),
                            'System' : MyColumn(col_type='string', column=model.System.fqdn, relations='system'),
                            'Arch' : MyColumn(col_type='string', column=model.Arch.arch, relations=['distro', 'arch']),
                            'Distro' : MyColumn(col_type='string', column=model.Distro.name, relations='distro'),
                            'Status' : MyColumn(col_type='string', column=model.TaskStatus.status, relations='status'),
                            'Result' : MyColumn(col_type='string', column=model.TaskResult.result, relations='result'),
                         }

    search_values_dict = {'Status' : lambda: model.TaskStatus.get_all_status(),
                          'Result' : lambda: model.TaskResult.get_all_results()}
    

class Task(SystemObject):
    search = TaskSearch
    searchable_columns = {
                          'Name' : MyColumn(col_type='string', column=model.Task.name),
                          'Description' : MyColumn(col_type='string', column=model.Task.description),
                          'Version' : MyColumn(col_type='string', column=model.Task.version),
                          'Types' : MyColumn(col_type='string',column=model.TaskType.type,relations=['types']),
                          'Arch' : MyColumn(col_type='string', column=model.Arch.arch,relations=['excluded_arch','arch']),
                          'Distro' : MyColumn(col_type='string', column=model.OSMajor.osmajor,relations=['excluded_osmajor','osmajor']),
                         }


    @classmethod
    def distro_is_filter(cls,x,y): 
        queri = model.Task.query().outerjoin(['excluded_osmajor','osmajor'])
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard
            osmajors = model.OSMajor.query().filter(model.OSMajor.osmajor.like(wildcard_y))
            osmajor_ids = [osmajor.id for osmajor in osmajors]
            if not osmajor_ids:
                return 'False'
            queri = queri.filter(model.OSMajor.osmajor.like(wildcard_y)) 
        else:
            try:
                model.OSMajor.query().filter(model.OSMajor.osmajor == y).one()
                wildcard = False
            except:
                return 'False'
            queri = queri.filter(model.OSMajor.osmajor == y)
        ids = [r.id for r in queri]

        #What this block is trying to do is determine if all the excluded distros of a particular task make up
        #all the distros, and thus leaving the task with no distro. Not likely, but we need to cater for this scenario
        #at least for sake of consistency.
        if not y:
            table = model.task_table.join(model.task_exclude_osmajor_table).join(model.osmajor_table)
            osmajor_queri = model.OSMajor.query()
            osmajor_ids = [r.id for r in osmajor_queri]
            last_teo_alias  = None
            for id in osmajor_ids:
                teo_alias = model.task_exclude_osmajor_table.alias()
                table = table.join(teo_alias,teo_alias.c.osmajor_id==id)
                last_teo_alias = teo_alias
            s = select([last_teo_alias.c.task_id],from_obj=table).group_by(last_teo_alias.c.task_id)           
            r = s.execute()
            ids = []
            for i in r:
                ids.append(i[0])
            return model.Task.id.in_(ids) 
        
        return not_(model.Task.id.in_(ids)) 
       

    @classmethod
    def arch_is_filter(cls,x,y): 
        queri = model.Task.query().outerjoin(['excluded_arch','arch'])
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard
            arches = model.Arch.query().filter(model.Arch.arch.like(wildcard_y))
            arch_ids = [arch.id for arch in arches]
            if not arch_ids:
                return 'False'
            queri = queri.filter(model.Arch.arch.like(wildcard_y))
            #return not_(x.like(wildcard_y))
        else:
            try:
                valid_arch = model.Arch.query().filter(model.Arch.arch == y).one()
            except:
                return 'False'
            queri = queri.filter(model.Arch.arch == y)
        log.debug(queri)
        ids = [r.id for r in queri]

        #What this block is trying to do is determine if all the excluded arches of a particular task make up
        #all the arches, and thus leaving the task with no arch. Not likely, but we need to cater for this scenario
        #at least for sake of consistency.
        if not y:
            table = model.task_table.join(model.task_exclude_arch_table).join(model.arch_table)
            arch_queri = model.Arch.query()
            arch_ids = [r.id for r in arch_queri]
            last_tea_alias  = None
            for id in arch_ids:
                tea_alias = model.task_exclude_arch_table.alias()
                table = table.join(tea_alias,tea_alias.c.arch_id==id)
                last_tea_alias = tea_alias
            s = select([last_tea_alias.c.task_id],from_obj=table).group_by(last_tea_alias.c.task_id)           
            r = s.execute()
            ids = []
            for i in r:
                ids.append(i[0])
            return model.Task.id.in_(ids) 
        
        return not_(model.Task.id.in_(ids)) 

    @classmethod
    def arch_is_not_filter(cls,x,y):
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard 
            arches = model.Arch.query().filter(model.Arch.arch.like(wildcard_y))
            arch_ids = [arch.id for arch in arches]
            if not arch_ids:
                return 'True'
            wildcard = True
            y = wildcard_y
        else:
        
            try:
                valid_arch = model.Arch.query().filter(model.Arch.arch == y).one()
                wildcard = False
            except:
                return 'True'
        return cls._opposites_is_not_filter(x,y,wildcard=wildcard)

    @classmethod
    def distro_is_not_filter(cls,x,y):
        wildcard_y = re.sub('\*','%',y)
        if wildcard_y != y: #looks like we found a wildcard 
            osmajors = model.OSMajor.query().filter(model.OSMajor.osmajor.like(wildcard_y))
            osmajor_ids = [osmajor.id for osmajor in osmajors]
            if not osmajor_ids:
                return 'True'
            wildcard = True
            y = wildcard_y
        else:
            try:
                model.OSMajor.query().filter(model.OSMajor.osmajor == y).one()
                wildcard = False
            except:
                return 'True'
        return cls._opposites_is_not_filter(x,y,wildcard)

    @classmethod
    def _opposites_is_not_filter(cls,x,y,wildcard):    
        if wildcard: #looks like we found a wildcard
            return x.like(y)
        if not y:
            return or_(x == None,x==y)
        return x == y

    @classmethod
    def arch_contains_filter(cls,x,y):
        return cls._opposites_contains_filter(x,y)

    @classmethod
    def distro_contains_filter(cls,x,y):
        return cls._opposites_contains_filter(x,y)

    @classmethod
    def _opposites_contains_filter(cls,col,val): 
        queri = model.Task.query().outerjoin(['excluded_arch','arch']).filter(model.Arch.arch.like('%%%s%%' % val))
        ids = [r.id for r in queri]
        return not_(model.Task.id.in_(ids))

class Distro(SystemObject):
    search = DistroSearch
    search_values_dict = { 'Virt' : ['True','False'] }
    searchable_columns = {
                            'Name' : MyColumn(col_type='string',column=model.Distro.name),
                            'InstallName' : MyColumn(col_type='string',column=model.Distro.install_name),
                            'OSMajor' : MyColumn(col_type='string',column=model.OSMajor.osmajor,relations=['osversion','osmajor']),
                            'Arch' : MyColumn(col_type='string',column=model.Arch.arch,relations='arch'),
                            'Virt' : MyColumn(col_type='boolean',column=model.Distro.virt),
                            'Method' : MyColumn(col_type='string',column=model.Distro.method),
                            'Breed' : MyColumn(col_type='string',column=model.Breed.breed, relations=['breed']),
                            'Tag' : MyColumn(col_type='string', column=model.DistroTag.tag, relations=['_tags'])
                         }
    search_values_dict = {'Tag' : lambda: [e.tag for e in model.DistroTag.list_by_tag('')]}

    @classmethod
    def tag_is_not_filter(cls,col,val):
        """
        tag_is_not_filter is a function dynamically called from append_results.
        """       
        if not val: 
           return or_(col != None, col != val) 
        else:
            #If anyone knows of a better way to do this, by all means...
            query = model.Distro.query().filter(model.Distro._tags.any(model.DistroTag.tag == val))       
          
        ids = [r.id for r in query]  
        return not_(model.distro_table.c.id.in_(ids)) 


class SystemReserve(System):
    search = SystemReserveSearch
    searchable_columns =  {
                            'Name'      : MyColumn(column=model.System.fqdn,col_type='string'),
                            'Type'      : MyColumn(column=model.SystemType.type, col_type='string', relations='type'), 
                            'Owner'     : MyColumn(column=model.User.user_name, col_type='string', has_alias=True, relations='owner'),
                            'Shared'    : MyColumn(column=model.System.shared, col_type='boolean'),
                            'User'      : MyColumn(column=model.User.user_name, col_type='string', has_alias=True, relations='user'),
                            'LoanedTo'  : MyColumn(column=model.User.user_name,col_type='string', has_alias=True, relations='loaned'),
                          }

    search_values_dict = dict(System.search_values_dict.items() +
                             [('Shared', lambda: ['True', 'False'])])
    

       
class Activity(SystemObject):
    search = ActivitySearch    
    searchable_columns = { 
                           'User' : MyColumn(col_type='string', column=model.User.user_name, relations='user'),
                           'Via' : MyColumn(col_type='string', column=model.Activity.service),
                           'System/Name' : MyColumn(col_type='string', column=model.System.fqdn, relations='object'), 
                           'Distro/Name': MyColumn(col_type='string', column=model.Distro.name, relations='object'),
                           'Property': MyColumn(col_type='string', column=model.Activity.field_name),
                           'Action' : MyColumn(col_type='string', column=model.Activity.action),
                           'Old Value' : MyColumn(col_type='string', column=model.Activity.old_value),
                           'New Value' : MyColumn(col_type='string', column=model.Activity.new_value),
                         }  

    @classmethod
    def SystemArch_is_not_filter(cls,col,val):
        """
        SystemArch_is_not_filter provides a custom filter for the System/Arch search.
        """
        if not val: 
           return or_(col != None, col != val) 
        else: 
            query = model.SystemActivity.query().join(['object','arch']).filter(model.Arch.arch == val)          
        ids = [r.id for r in query]  
        return not_(model.activity_table.c.id.in_(ids)) 
        

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
    searchable_columns = {'Value': KeyColumn(relations=[['key_values_int','key'],['key_values_string','key']])}
    search = KeySearch
    
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
            return 'int'    
        elif int_table == 0:
            return 'string'
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
    def value_less_than_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
        return and_(model.Key_Value_Int.key_value < val, model.Key_Value_Int.key_id == key_id)

    @classmethod
    def value_greater_than_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name) 
        int_table = result.numeric
        key_id = result.id
        return and_(model.Key_Value_Int.key_value > val, model.Key_Value_Int.key_id == key_id)

    @classmethod
    def value_contains_filter(cls, col, val, key_name):
        result = model.Key.by_name(key_name) 
        key_id = result.id
        return and_(model.Key_Value_String.key_value.like('%%%s%%' % val),model.Key_Value_String.key_id == key_id) 
        
    @classmethod
    def value_is_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name) 
        int_table = result.numeric
        key_id = result.id
       
        if int_table == 1:
            if not val:
                return and_(or_(model.Key_Value_Int.key_value == val,model.Key_Value_Int.key_value == None),or_(model.Key_Value_Int.key_id == key_id,model.Key_Value_Int.key_id == None))    
            else:
                return and_(model.Key_Value_Int.key_value == val,model.Key_Value_Int.key_id == key_id)
        elif int_table == 0:
            if not val:
                return and_(or_(model.Key_Value_String.key_value == val,model.Key_Value_String.key_value == None),or_(model.Key_Value_String.key_id == key_id,model.Key_Value_String.key_id == None))
            else:
                 return and_(model.Key_Value_String.key_value == val,model.Key_Value_String.key_id == key_id) 

    @classmethod
    def value_is_not_filter(cls,col,val,key_name):
        result = model.Key.by_name(key_name)
        int_table = result.numeric
        key_id = result.id
       
        if int_table == 1:
            if val:
                return and_(or_(model.Key_Value_Int.key_value != val,model.Key_Value_Int.key_value == None), or_(model.Key_Value_Int.key_id == key_id,model.Key_Value_Int.key_id == None))
            else:
                return and_(model.Key_Value_Int.key_value != val, model.Key_Value_Int.key_id == key_id)
        elif int_table == 0:
            if val:
                return and_(or_(model.Key_Value_String.key_value != val,model.Key_Value_String.key_value == None), or_(model.Key_Value_String.key_id == key_id, model.Key_Value_String.key_id == None))         
            else:
                return and_(model.Key_Value_String.key_value != val, model.Key_Value_String.key_id == key_id)

class Job(SystemObject):
    search = JobSearch
    display_name='Job'
    searchable_columns = {
                           'Id' : MyColumn(col_type='numeric',column=model.Job.id), 
                           'Owner' : MyColumn(col_type='string',column=model.User.email_address, relations='owner'),
                           'Status' : MyColumn(col_type='string', column=model.TaskStatus.status, relations='status'),
                           'Result' : MyColumn(col_type='string',column=model.TaskResult.result, relations='result'),
                           'Whiteboard' : MyColumn(col_type='string', column=model.Job.whiteboard)

                         }

    search_values_dict = {'Status' : lambda: model.TaskStatus.get_all_status(),
                          'Result' : lambda: model.TaskResult.get_all_results()}
                         
            
class Cpu(SystemObject):      
    display_name = 'CPU'   
    search_values_dict = { 'Hyper' : lambda: ['True','False'] }
    searchable_columns = {
                          'Vendor'      : CpuColumn(col_type='string', column = model.Cpu.vendor),
                          'Processors'  : CpuColumn(col_type='numeric',column = model.Cpu.processors),
                          'Hyper'       : CpuColumn(col_type='boolean',column = model.Cpu.hyper),
                          'Cores'       : CpuColumn(col_type='numeric',column = model.Cpu.cores),
                          'Sockets'     : CpuColumn(col_type='numeric',column = model.Cpu.sockets),
                          'Model'       : CpuColumn(col_type='numeric',column = model.Cpu.model),
                          'ModelName'   : CpuColumn(col_type='string',column = model.Cpu.model_name),
                          'Family'      : CpuColumn(col_type='numeric',column = model.Cpu.family),
                          'Stepping'    : CpuColumn(col_type='numeric',column = model.Cpu.stepping),
                          'Speed'       : CpuColumn(col_type='numeric',column = model.Cpu.speed),
                          'Flags'       : CpuColumn(col_type='string',column = model.CpuFlag.flag, relations=['cpu','flags']) 
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
            query = model.Cpu.query().filter(model.Cpu.flags.any(model.CpuFlag.flag == val))
            ids = [r.id for r in query]
            return or_(not_(model.cpu_table.c.id.in_(ids)), col == None) 
         
class Device(SystemObject):
    display_name = 'Devices'
    searchable_columns = {'Description' : DeviceColumn(col_type='string', column=model.Device.description),
                          'Vendor_id' : DeviceColumn(col_type='string', column=model.Device.vendor_id),
                          'Device_id' : DeviceColumn(col_type='string', column=model.Device.device_id),
                          'Driver' : DeviceColumn(col_type='string', column=model.Device.driver)  } 
      
    @classmethod
    def driver_is_not_filter(cls,col,val):
        if not val:
            return or_(col != None, col != val)
        else:
            query = model.System.query().filter(model.System.devices.any(model.Device.driver == val))
    
        ids = [r.id for r in query]  
        return not_(model.system_table.c.id.in_(ids))   
