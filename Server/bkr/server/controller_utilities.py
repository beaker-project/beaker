from turbogears import widgets
from model import *
import search_utility
import bkr
import bkr.server.stdvars
from bkr.server.widgets import myPaginateDataGrid
from cherrypy import request, response
from bkr.server.needpropertyxml import *
from bkr.server.helpers import *
from bexceptions import *
import re


# for debugging
import sys

# from bkr.server import json
import logging
log = logging.getLogger("bkr.server.controllers")

class Utility:
    #I this I will move this Utility class out into another module and then
    #perhaps break it down into further classes. Work from other tickets
    #is making it quite large.

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
    def get_correct_system_column(cls,x):
        if type(x) == type(()):
            return x[0] 
        else:
            return x

    @classmethod
    def system_name_name(cls):
        return 'fqdn'

    @classmethod
    def system_powertype_name(cls):
        return 'power'

    @classmethod
    def get_attr(cls,c):        
        return lambda x:getattr(cls.get_correct_system_column(x),c.lower()) 

    @classmethod
    def system_loanedto_getter(cls):
        return lambda x: x.loaned
          
    @classmethod
    def system_powertype_getter(cls):
        def my_f(x):
            try:
                return cls.get_correct_system_column(x).power.power_type.name  
            except Exception,(e): 
                return ''   
        return my_f

    @classmethod
    def system_arch_getter(cls):
        return lambda x: ', '.join([arch.arch for arch in cls.get_correct_system_column(x).arch])  

    @classmethod
    def system_name_getter(cls):
        return lambda x: make_link("/view/%s" % cls.get_correct_system_column(x).fqdn, cls.get_correct_system_column(x).fqdn)

    @classmethod
    def get_attr_other(cls,index):
        return lambda x: x[index]

    @classmethod 
    def custom_systems_grid(cls,systems,others=None):
   
        def get_widget_attrs(table,column,with_desc=True,sortable=False,index=None): 
            options = {}
            lower_column = column.lower()
            lower_table = table.lower()

            name_function_name = '%s_%s_name' % (lower_table, lower_column)
            custom_name = getattr(Utility,name_function_name,None)

            getter_function_name = '%s_%s_getter' % (table.lower(), column.lower())
            custom_getter = getattr(Utility, getter_function_name,None)

            if custom_name:
                lower_column = custom_name()

            if custom_getter: 
                my_getter = custom_getter()
            elif index is not None:         
                my_getter = Utility.get_attr_other(index_in_queri)
            else:
                my_getter = Utility.get_attr(column)

            if with_desc: 
                title_string = '%s-%s' % (table,column)
            else: 
                title_string = '%s' % column
             
            if sortable:
                options['sortable'] = True
                name_string = '%s' % lower_column  #sortable columns need a real name
            else:
                options['sortable'] = False 
                name_string = '%s.%s' % (lower_table,lower_column)
         
            return name_string,title_string,options,my_getter

        fields = []
        if systems:
            options = {} 
            for column_desc in systems: 
                table,column = column_desc.split('/')
                if column.lower() in ('name','vendor','memory','model','location'):
                    sort_me = True
                else:
                    sort_me = False

                if others:
                    (name_string, title_string, options, my_getter) = get_widget_attrs(table, column, with_desc=True, sortable=sort_me)
                else:
                    (name_string, title_string, options, my_getter) = get_widget_attrs(table, column, with_desc=False, sortable=True)

                new_widget = widgets.PaginateDataGrid.Column(name=name_string, getter=my_getter, title=title_string, options=options) 
                if column == 'Name':
                    fields.insert(0,new_widget)
                else:
                    fields.append(new_widget)

        if others:
            for index,column_desc in enumerate(others):  
                table,column = column_desc.split('/') 
                index_in_queri = index + 1
                (name_string, title_string, options, my_getter) = get_widget_attrs(table, column, with_desc=True, 
                                                                                   sortable=False, index=index_in_queri)
                new_widget = widgets.PaginateDataGrid.Column(name=name_string , 
                                                             getter = my_getter, 
                                                             title=title_string, 
                                                             options=options) 
                fields.append(new_widget)
        return fields

    @classmethod
    def status_id_change_handler(cls,current_val,new_val,**kw): 
        bad_status = ['broken','removed']
        new_status = SystemStatus.by_id(new_val)
        if new_status.status.lower() == 'working': 
            if current_val:
                old_status = SystemStatus.by_id(current_val)
                if old_status.status.lower() in bad_status:
                    kw['status_reason'] = None  #remove the status notes
        return kw           
