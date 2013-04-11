from turbogears import widgets
from kid.element import Element
from model import *
import search_utility
import bkr
import bkr.server.stdvars
from bkr.server.widgets import myPaginateDataGrid
from cherrypy import request, response, HTTPError
from bkr.server.helpers import *
from bexceptions import *
import re


# for debugging
import sys

# from bkr.server import json
import logging
log = logging.getLogger("bkr.server.controllers")


def _custom_status(x):
    if x.is_dirty:
        e = Element('span', {'class': 'statusDirty'})
        e.text = u'Updating\u2026'
        return e
    e = Element('span', {'class' : 'status%s' % x.status})
    e.text = x.status
    return e

def _custom_result(x):
    e = Element('span', {'class' : 'result%s' % x.result})
    e.text = x.result
    return e

class _FKLogEntry:
    def __init__(self,form_field,mapper_class,mapper_column_name,description=None):
        if description is None:
            log.debug('No description passed to %s, using form_field value of %s instead' % (self.__class__.__name__,form_field))
        self.description = description or form_field
        self.form_field = form_field
        self.mapper_class = mapper_class
        valid_column = getattr(mapper_class,mapper_column_name,None)
        self.mapper_column_name = mapper_column_name


class SystemTab:

    @classmethod
    def get_provision_perms(cls, system, our_user, currently_held):

        if system.can_share(our_user) and system.can_provision_now(our_user): #Has privs and machine is available, can take
            provision_now_rights = False
            will_provision = True # User with take privs can also schedule it they wish
            provision_action = '/schedule_provision'
        elif not system.can_provision_now(our_user): # If you don't have privs to take
            if system.is_available(our_user): #And you have access to the machine, schedule
                provision_action = '/schedule_provision'
                provision_now_rights = False
                will_provision = True
            else: #No privs to machine at all
                will_provision = False
                provision_now_rights = False
                provision_action = ''
        elif system.can_provision_now(our_user) and currently_held: #Has privs, and we are current user, we can provision
            provision_action = '/action_provision'
            provision_now_rights = True
            will_provision = True
        elif system.can_provision_now(our_user) and not currently_held: #Has privs, not current user, You need to Take it first
            provision_now_rights = False
            will_provision = True
            provision_action = '/schedule_provision'
        else:
            log.error('Could not follow logic when determining user access to machine')
            will_provision = False
            provision_now_rights = False
            provision_action = ''

        return provision_now_rights,will_provision,provision_action


class _SystemSaveFormHandler:

    @classmethod
    def status_change_handler(cls,current_val,new_val,**kw): 
        if not new_val.bad and current_val and current_val.bad:
            kw['status_reason'] = None  #remove the status notes
        return kw 


class SystemSaveForm:
    handler = _SystemSaveFormHandler
    fk_log_entry = _FKLogEntry 


class SearchOptions:
    
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



class Utility:

    @classmethod
    def direct_column(cls,title,getter):
        """
        direct_column() will return a DataGrid Column and is intended to be used to generate 
        columns to be inserted into a grid without any other sideaffects (unlike custom_systems_grid()).
        They are also free of control from other elemnts such as the result_columns()
        """
        col = widgets.DataGrid.Column(name=title, title=title, getter=getter)
        return col

    @classmethod
    def result_columns(cls,values_checked = None):  
      """
      result_columns() will return the list of columns that are able to bereturned
      in the system search results.
      """
      column_names = search_utility.System.search.create_column_table([{search_utility.Cpu :{'exclude': ['Flags']} },
                                                                       {search_utility.System: {'all':[]} }] ) 
      
      send = [(elem,elem) for elem in column_names]  
     
      if values_checked is not None:
         vals_to_set = values_checked
         response.simple_cookie['column_values'] = ','.join(values_checked)
      elif request.simple_cookie.has_key('column_values'): 
         text = request.simple_cookie['column_values'].value
         vals_to_set = text.split(',') 
      else:
         vals_to_set = [] 

      default = {}
      for elem in vals_to_set:
          default[elem] = 1;

      return {'options' : send, 'default':default}; 

    @classmethod
    def cpu_vendor_getter_name(cls):
        return 'cpu.vendor'

    @classmethod
    def cpu_stepping_getter_name(cls):
        return 'cpu.stepping'

    @classmethod
    def cpu_speed_getter_name(cls):
        return 'cpu.speed'

    @classmethod
    def cpu_sockets_getter_name(cls):
        return 'cpu.sockets'

    @classmethod
    def cpu_modelname_getter_name(cls):
        return 'cpu.model_name'

    @classmethod
    def cpu_model_getter_name(cls):
        return 'cpu.model'

    @classmethod
    def cpu_hyper_getter_name(cls):
        return 'cpu.hyper'

    @classmethod
    def cpu_family_getter_name(cls):
        return 'cpu.family'

    @classmethod
    def cpu_processors_getter_name(cls):
        return 'cpu.processors'

    @classmethod
    def cpu_cores_getter_name(cls):
        return 'cpu.cores'

    @classmethod
    def system_name_name(cls):
        return 'fqdn'

    @classmethod
    def system_arch_name(cls):
        return 'arch.arch'

    @classmethod
    def system_user_name(cls):
        return 'user.user_name'

    @classmethod
    def system_powertype_name(cls):
        return 'power.power_type.name'

    @classmethod
    def system_serialnumber_name(cls):
        return 'serial'

    @classmethod
    def get_attr(cls,c):
        return lambda x:getattr(x,c.lower())

    @classmethod
    def system_group_getter(cls):
        return lambda x: ' '.join([group.group_name for group in x.groups])

    @classmethod
    def system_numanodes_getter(cls):
        return lambda x: getattr(x.numa, 'nodes', 0)

    @classmethod
    def system_added_getter(cls):
        return lambda x: x.date_added

    @classmethod
    def system_loanedto_getter(cls):
        return lambda x: x.loaned
          
    @classmethod
    def system_powertype_getter(cls):
        def my_f(x):
            try:
                return x.power.power_type.name
            except Exception,(e):
                return ''
        return my_f

    @classmethod
    def system_arch_getter(cls):
        return lambda x: ', '.join([arch.arch for arch in x.arch])  

    @classmethod
    def system_name_getter(cls):
        return lambda x: make_link("/view/%s" % x.fqdn, x.fqdn)

    @classmethod
    def system_loancomment_getter(cls):
        # Return only first 70 chars of loan comment
        return lambda x: x.loan_comment[:70] if x.loan_comment else \
            x.loan_comment

    @classmethod
    def system_serialnumber_getter(cls):
        return lambda x: x.serial

    @classmethod
    def system_added_options(cls):
        return dict(datetime=True)

    @classmethod
    def _get_nested_attr(cls, attrs):
        def f(obj):
            for attr in attrs.split('.'):
                if obj:
                    obj = getattr(obj, attr)
            return obj
        return f

    @classmethod 
    def custom_systems_grid(cls, systems, others=False):
   
        def get_widget_attrs(table,column,with_desc=True,sortable=False,index=None):
            options = {}
            name_string = lower_column = column.lower()
            lower_table = table.lower()
            name_getter_function_name = '%s_%s_getter_name' % (lower_table, lower_column)
            custom_name_getter = getattr(Utility, name_getter_function_name, None)
            if custom_name_getter:
                name = getter = custom_name_getter()
                my_getter =  cls._get_nested_attr(getter)
                name_string = name.lower()
            else:
                name_function_name = '%s_%s_name' % (lower_table, lower_column)
                custom_name = getattr(Utility, name_function_name, None)
                if custom_name:
                    name_string = custom_name()

                getter_function_name = '%s_%s_getter' % (lower_table, lower_column)
                custom_getter = getattr(Utility, getter_function_name, None)
                if custom_getter:
                    my_getter = custom_getter()
                else:
                    my_getter = Utility.get_attr(column)

            if with_desc:
                title_string = '%s-%s' % (table,column)
            else:
                title_string = '%s' % column
             
            if sortable:
                options['sortable'] = True
            else:
                options['sortable'] = False
                name_string = '%s.%s' % (lower_table, lower_column)

            options_function_name = '%s_%s_options' % (lower_table, lower_column)
            custom_options = getattr(Utility, options_function_name, None)
            if custom_options:
                options.update(custom_options())

            return name_string,title_string,options,my_getter

        fields = []
        if systems:
            for column_desc in systems:
                table,column = column_desc.split('/')
                if column.lower() in ('name', 'vendor', 'lender', 'location',
                        'memory', 'model', 'location', 'status', 'user',
                        'type', 'powertype'):
                    sort_me = True
                else:
                    sort_me = False

                if others:
                    (name_string, title_string, options, my_getter) = get_widget_attrs(table, column, with_desc=True, sortable=sort_me)
                else:
                    (name_string, title_string, options, my_getter) = get_widget_attrs(table, column, with_desc=False, sortable=sort_me)

                new_widget = widgets.PaginateDataGrid.Column(name=name_string, getter=my_getter, title=title_string, options=options)
                if column == 'Name':
                    fields.insert(0, new_widget)
                else:
                    fields.append(new_widget)

        return fields

def restrict_http_method(method):
    def outer(fn):
        def inner(*args, **kw):
            accepted_method = method.lower()
            request_method = request.method.lower()
            if not request_method == accepted_method:
                request_with = request.headers.get("X-Requested-With", None)
                err_msg = "Unable to call %s with method %s" % (fn, request_method.upper())
                if request_with == 'XMLHttpRequest':
                    response.status = 405
                    return [err_msg]
                else:
                    raise HTTPError(status=405, message=err_msg)
            else:
                return fn(*args, **kw)
        return inner
    return outer
