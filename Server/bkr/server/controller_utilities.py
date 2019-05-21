
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import widgets
from kid.element import Element
from cherrypy import request, response, HTTPError
from bkr.server import search_utility
from bkr.server.helpers import make_link

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
    def system_labcontroller_name(cls):
        return 'lab_controller.fqdn'

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
    def system_reserved_name(cls):
        return 'open_reservation.start_time'

    @classmethod
    def system_reserved_getter(cls):
        return lambda x: x.open_reservation.start_time if x.open_reservation is not None else ''

    @classmethod
    def system_pools_getter(cls):
        return lambda x: ' '.join([pool.name for pool in x.pools])

    @classmethod
    def system_numanodes_getter(cls):
        return lambda x: getattr(x.numa, 'nodes', 0)

    @classmethod
    def system_notes_getter(cls):
        return lambda x: ' ---- '.join([note.text for note in x.notes])

    @classmethod
    def system_added_getter(cls):
        return lambda x: x.date_added

    @classmethod
    def system_lastinventoried_getter(cls):
        return lambda x: x.date_lastcheckin

    @classmethod
    def system_loanedto_getter(cls):
        return lambda x: x.loaned
          
    @classmethod
    def system_powertype_getter(cls):
        def my_f(x):
            try:
                return x.power.power_type.name
            except Exception:
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
    def system_labcontroller_getter(cls):
        return lambda x: x.lab_controller

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

            return dict(name=name_string, title=title_string, options=options, getter=my_getter)

        fields = []
        systems = sorted(list(systems))
        if systems:
            default_result_column_order = (
                'System/Name',
                'System/Arch',
                'System/Vendor',
                'System/Model',
            )
            widget_attrs = []

            for column_desc in default_result_column_order:
                table, column = column_desc.split('/')
                if column_desc in systems:
                    widget_attrs.append((table, column))

            for column_desc in systems:
                if column_desc in default_result_column_order:
                    continue

                table, column = column_desc.split('/')
                widget_attrs.append((table, column))

            for table, column in widget_attrs:
                attrs = get_widget_attrs(table, column, with_desc=others, sortable=field_is_sortable(column))
                widget = widgets.PaginateDataGrid.Column(**attrs)
                fields.append(widget)

        return fields

# TODO: Modify query for sorting to support aliases or multiple identical values. Bugzilla: 1680536
def field_is_sortable(column):
    sortable_fields = (
        'name',
        'vendor',
        'lender',
        'location',
        'memory',
        'model',
        'location',
        'status',
        'user',
        'reserved',
        'type',
        'powertype',
        'labcontroller'
    )
    return column.lower() in sortable_fields


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
