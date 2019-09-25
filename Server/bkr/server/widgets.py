
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import validators, url, config
from kid import Element
import time
import turbogears as tg
from bkr.server.stdvars import jsonify_for_html
from turbogears.widgets.rpc import RPC
from sqlalchemy import distinct
import re
import random
import search_utility
from decimal import Decimal
from itertools import chain
from turbogears import widgets
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea, Label,
                                SingleSelectField, CheckBox, 
                                HiddenField, RemoteForm, LinkRemoteFunction, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, DataGrid, RepeatingFormField,
                                CompoundWidget, AjaxGrid, CSSLink,
                                MultipleSelectField, Button,
                                RepeatingFieldSet, SelectionField, WidgetsList,
                                PasswordField)

from bkr.server import model, search_utility, identity
from bkr.server.model import TaskStatus
from bkr.server.assets import get_assets_env
from bkr.server.bexceptions import BeakerException
from bkr.server.helpers import make_link
from bkr.server.util import VALID_FQDN_REGEX
import logging
log = logging.getLogger(__name__)

class AutoCompleteTextField(widgets.AutoCompleteTextField):


    template="""
    <span xmlns:py="http://purl.org/kid/ns#" class="${field_class}">
    <script type="text/javascript">
        AutoCompleteManager${field_id} = new AutoCompleteManager('${field_id}', '${field_id}', null,
        '${search_controller}', '${search_param}', '${result_name}', ${str(only_suggest).lower()},
        '${show_spinner and tg.url('/tg_widgets/turbogears.widgets/spinner.gif') or None}',
        ${complete_delay}, ${str(take_focus).lower()}, ${min_chars});
        addLoadEvent(AutoCompleteManager${field_id}.initialize);
    </script>
    <input type="text" name="${name}" class="${field_class}" id="${field_id}"
        value="${value}" py:attrs="attrs"/>
    <img py:if="show_spinner" id="autoCompleteSpinner${field_id}"
        src="${tg.url('/tg_widgets/turbogears.widgets/spinnerstopped.png')}" alt=""/>
    <span class="autoTextResults" id="autoCompleteResults${field_id}"/>
    </span>
    """

class AutoCompleteField(widgets.AutoCompleteField):
    """Text field with auto complete functionality and hidden key field."""

    template = """
    <span xmlns:py="http://purl.org/kid/ns#" id="${field_id}" class="${field_class}">
    <script type="text/javascript">
        AutoCompleteManager${field_id} = new AutoCompleteManager('${field_id}',
        '${text_field.field_id}', '${hidden_field.field_id}',
        '${search_controller}', '${search_param}', '${result_name}',${str(only_suggest).lower()},
        '${show_spinner and tg.url('/tg_widgets/turbogears.widgets/spinner.gif') or None}',
        ${complete_delay}, ${str(take_focus).lower()}, ${min_chars});
        addLoadEvent(AutoCompleteManager${field_id}.initialize);
    </script>
    ${text_field.display(value_for(text_field), **params_for(text_field))}
    <img py:if="show_spinner" id="autoCompleteSpinner${field_id}"
        src="${tg.url('/tg_widgets/turbogears.widgets/spinnerstopped.png')}" alt=""/>
    <span class="autoTextResults" id="autoCompleteResults${field_id}"/>
    ${hidden_field.display(value_for(hidden_field), **params_for(hidden_field))}
    </span>
    """


class Hostname(validators.Regex):
    messages = {'invalid': 'The supplied value is not a valid hostname'}
    def __init__(self, **kwargs):
        super(Hostname, self).__init__(
            VALID_FQDN_REGEX, strip=True, **kwargs)

    def _to_python(self, value, state):
        # Hostnames are case-insensitive, so let's force it to lowercase here 
        # for consistency
        return super(Hostname, self)._to_python(value, state).lower()

class ValidEnumValue(validators.FancyValidator):
    def __init__(self, enum_type):
        super(ValidEnumValue, self).__init__()
        self.enum_type = enum_type
    def _to_python(self, value, state):
        try:
            return self.enum_type.from_string(value)
        except ValueError:
            raise validators.Invalid(self.message('invalid', state), value, state)
    def _from_python(self, value, state):
        return value.value

class LocalJSLink(JSLink):
    """
    Link to local Javascript files
    """
    order = 10
    def update_params(self, d): 
        super(LocalJSLink, self).update_params(d)
        d["link"] = url(self.name)


class LocalCSSLink(CSSLink):
    """
    Link to local CSS files
    """
    def update_params(self, d):
        super(LocalCSSLink, self).update_params(d)
        d["link"] = self.name


class LocalJSBundleLink(LocalJSLink):

    template = """
        <script xmlns:py="http://purl.org/kid/ns#"
            py:for="url in urls"
            type="text/javascript" src="$url" />
        """

    def __init__(self, name, **kwargs):
        super(LocalJSBundleLink, self).__init__('bkr.server', name, **kwargs)

    def update_params(self, d):
        super(LocalJSBundleLink, self).update_params(d)
        bundle = get_assets_env()[self.name]
        d['urls'] = [url(u) for u in bundle.urls()]


class LocalCSSBundleLink(LocalCSSLink):

    template = """
        <link xmlns:py="http://purl.org/kid/ns#"
            py:for="url in urls"
            rel="stylesheet" type="text/css" media="$media"
            href="$url" />
        """

    def __init__(self, name, **kwargs):
        super(LocalCSSBundleLink, self).__init__('bkr.server', name, **kwargs)

    def update_params(self, d):
        super(LocalCSSBundleLink, self).update_params(d)
        bundle = get_assets_env()[self.name]
        d['urls'] = [url(u) for u in bundle.urls()]


jquery = LocalJSLink('bkr', '/static/javascript/jquery-2.0.2.min.js',
        order=1) # needs to come after MochiKit
beaker_js = LocalJSBundleLink('js', order=5)
beaker_css = LocalCSSBundleLink('css')


class HorizontalForm(Form):
    template = 'bkr.server.templates.horizontal_form'
    params = ['legend_text']


class InlineForm(Form):
    template = 'bkr.server.templates.inline_form'

class InlineRemoteForm(RPC, InlineForm):

    # copied from turbogears.widgets.RemoteForm
    def update_params(self, d):
        super(InlineRemoteForm, self).update_params(d)
        d['form_attrs']['onSubmit'] = "return !remoteFormRequest(this, '%s', %s);" % (
            d.get("update", ''), jsonify_for_html(self.get_options(d)))


class RadioButtonList(SelectionField):
    template = """
    <div xmlns:py="http://purl.org/kid/ns#" py:strip="True">
        <label py:for="value, desc, attrs in options" class="radio">
            <input type="radio"
                name="${name}"
                id="${field_id}_${value}"
                value="${value}"
                py:attrs="attrs"
            />
            ${desc}
        </label>
    </div>
    """
    _selected_verb = 'checked'

class CheckBoxList(SelectionField):
    template = """
    <div xmlns:py="http://purl.org/kid/ns#" py:strip="True">
        <label py:for="value, desc, attrs in options" class="radio">
            <input type="checkbox"
                name="${name}"
                id="${field_id}_${value}"
                value="${value}"
                py:attrs="attrs"
            />
            ${desc}
        </label>
    </div>
    """
    _multiple_selection = True
    _selected_verb = 'checked'


class UnmangledHiddenField(HiddenField):

    @property
    def field_id(self):
        return self.name

    def update_params(self, d):
        super(UnmangledHiddenField, self).update_params(d)
        d['name'] = self.name


class DeleteLinkWidget(Widget):
    javascript = [LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),
        LocalJSLink('bkr', '/static/javascript/util.js')]
    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    params = ['msg', 'action_text', 'show_icon']
    msg = None
    action_text = _(u'Delete')
    show_icon = True

class DoAndConfirmForm(Form):
    """Generic confirmation dialogue


    DoAndConfirmForm is a way of providing consistent look and feel
    for confirmation dialogue boxes. It provides either a href anchor
    or button element.

    XXX This could be further rationalised with DeleteLinkWidgetForm
    """

    template = "bkr.server.templates.do_and_confirm"
    params = ['msg', 'action_text', 'look']

    def __init__(self, *args, **kw):
        self.javascript.extend([LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),
            LocalJSLink('bkr', '/static/javascript/util.js'),])
        self.css.append(LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css'))

    def update_params(self, d):
        super(DoAndConfirmForm, self).update_params(d)
        form_args = d['value']
        d['hidden_fields'] = []
        for id, val in form_args.items():
            hidden_field = UnmangledHiddenField(id, attrs={'value' : val })
            d['hidden_fields'].append(hidden_field)

class DeleteLinkWidgetForm(Form, DeleteLinkWidget):
    template = """
    <span xmlns:py='http://purl.org/kid/ns#' py:strip='1'>
      <form action="${action}" method="post">
        <script>
          var action = function(form_node) { return function() { form_node.submit(); }}
          var job_delete = function (form_node) {
            do_and_confirm_form('${msg}', 'delete', action(form_node));
          }
        </script>
        <span py:for="field in hidden_fields"
          py:replace="field.display()"/>
            <a href="#" onclick="javascript:job_delete(this.parentNode);return false;" 
               class="btn">
              <i class="fa fa-times" py:if="show_icon"/> ${action_text}
            </a>
      </form>
    </span>
    """
    params = ['msg', 'action_text']

    def update_params(self, d):
        super(DeleteLinkWidgetForm, self).update_params(d)
        form_args = d['value']
        d['hidden_fields'] = []
        for id, val in form_args.items():
            hidden_field = UnmangledHiddenField(id, attrs={'value' : val })
            d['hidden_fields'].append(hidden_field)


class DeleteLinkWidgetAJAX(DeleteLinkWidget):

    template="""<a xmlns:py='http://purl.org/kid/ns#' class="btn" href="#"
        onclick="javascript:do_and_confirm_ajax('${action}', ${data}, ${callback},
        '${msg}', '${action_type}');return false">
            <i class="fa fa-times" py:if="show_icon"/> ${action_text}
        </a>"""
    params = ['data', 'callback', 'action_type']

    def display(self, value=None, **params):
        missing = [(i, True) for i in ['action', 'data', 'callback']
                      if not params.get(i)]
        if any(missing):
            raise ValueError('Missing arguments to %s: %s' %
                (self.__class__.__name__, ','.join(dict(missing).keys())))
        params['action_type'] = params.get('action_type', 'delete')
        params['data'] = jsonify_for_html(params['data'])
        return super(DeleteLinkWidgetAJAX, self).display(value, **params)


class MyButton(Button):
    template="bkr.server.templates.my_button"
    params = ['type', 'button_label', 'name']
    def __init__(self, name, type="submit", button_label=None, *args, **kw):
        super(MyButton,self).__init__(*args, **kw)
        self.type = type
        self.name = name
        self.button_label = button_label

    def display(self, value=None, **params):
        if 'options' in params:
            if 'label' in params['options']:
                params['button_label'] = params['options']['label']
            if 'name' in params['options']:
                params['name'] = params['options']['name']
        return super(MyButton,self).display(value,**params)

class BeakerDataGrid(DataGrid):
    template = "bkr.server.templates.beaker_datagrid"
    name = "beaker_datagrid"


class MatrixDataGrid(DataGrid):
    template = "bkr.server.templates.matrix_datagrid"
    name = "matrix_datagrid"
    TASK_POS = 0
    params = ['TASK_POS']

    class Column(DataGrid.Column):
        def __init__(self,*args, **kw):
            outer_header = None
            type = None
            if 'name' in kw:
                #Make sure the random number is removed when displaying
                kw['name'] =  "%s_%s" % (kw['name'], random.random())
            if 'outer_header' in kw:
                self.outer_header = kw['outer_header']
                del kw['outer_header']
            if 'type' in kw:
                self.type = kw['type']
                del kw['type']
            if 'order' in kw:
                order = kw['order']
                self.order = order
                del kw['order']

            DataGrid.Column.__init__(self, *args, **kw) #Old style object

    def _header_cmp(self,x,y):
        x_order = x[2]
        y_order = y[2]
        #anything with order goes before
        if x_order is not None and y_order is None:
            return -1
        elif x_order is None and y_order is not None:
            return 1
        elif x_order is None and y_order is None:
            #if no order, order by header
            x_header = x[0]
            y_header = y[0]
            if x_header < y_header:
                return -1
            else:
                return 1

    def update_params(self, d):
        super(MatrixDataGrid,self).update_params(d)
        headers = {}
        header_order = {}
        orders_used = []
        cant_use_header = False
        must_use_header = False
        for col in self.columns:
            try:
                order = col.order
            except AttributeError:
                order = None
            else:
                try:
                    orders_used.index(order)
                    raise BeakerException('Order number %s has already been specified,it cannot be specified twice' % order)
                except ValueError, e:
                    orders_used.append(order)
            try:
                header_order[col.outer_header] = order
            except AttributeError:
                cant_use_header = True
            else:
                must_use_header = True
                if headers.get(col.outer_header):
                    headers[col.outer_header] += 1
                else:
                    headers[col.outer_header] = 1
            if cant_use_header and must_use_header:
                raise ValueError("All Columns must be \
                    unified in their use of outer headers")

        decorated_headers = [(header, occurance, header_order[header]) for header,occurance in headers.items()]
        sorted_decorated_headers = sorted(decorated_headers, cmp=self._header_cmp)
        d['outer_headers'] = [(header,occurance) for header,occurance,order in sorted_decorated_headers]
        if must_use_header:
            # Ensures that columns are sorted in the same manner as outer_headers
            columns = [column_to_sort for column_to_sort in d['columns'] if \
                getattr(column_to_sort,'outer_header', None) is None]
            columns_to_sort = [column_to_sort for \
                column_to_sort in d['columns'] if \
                    getattr(column_to_sort,'outer_header', None) is not None]
            columns += sorted(columns_to_sort, key=lambda col: col.outer_header)
            d['columns'] = columns

class myPaginateDataGrid(PaginateDataGrid):
    template = "bkr.server.templates.my_paginate_datagrid"
    params = ['add_action', 'add_script']

class SingleSelectFieldJSON(SingleSelectField):
    params = ['for_column']
    def __init__(self,*args,**kw):
        super(SingleSelectFieldJSON, self).__init__(*args, **kw)

        if kw.has_key('for_column'):
            self.for_column = kw['for_column']

    def __json__(self):
        return_dict = {}
        return_dict['field_id'] = self.field_id
        return_dict['name'] = self.name
        if hasattr(self,'for_column'):
            return_dict['column'] = self.for_column
        return return_dict


class TextFieldJSON(TextField):
    def __json__(self):
        return {
                'field_id' : self.field_id,             
               }


class NestedGrid(CompoundWidget):
    template = "bkr.server.templates.inner_grid" 
    params = ['inner_list']


class JobQuickSearch(CompoundWidget):
    template = 'bkr.server.templates.quick_search'
    member_widgets = ['status_running','status_queued']

    def __init__(self,*args,**kw): 
        self.status_running = Button(default="Status is Running",
                                     name='status_running',
                                     attrs = {'onclick' : "document.location.href('./?jobsearch-0.table=Status&jobsearch-0.operation=is&jobsearch-0.value=Running&Search=Search')" })

        self.status_queued = Button(default="Status is Queued", name='status_queued')

class AckPanel(RadioButtonList):

    javascript = [LocalJSLink('bkr','/static/javascript/jquery-ui-1.9.2.min.js', order=3),
                  LocalJSLink('bkr','/static/javascript/loader_v2.js'),
                  LocalJSLink('bkr','/static/javascript/response_v6.js')]

    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    params = ['widget_name']
    template = """
    <div xmlns:py="http://purl.org/kid/ns#"
        class="${field_class}"
        id="${field_id}"
    >
        <label py:for="value, desc, attrs in options" class="radio">
            <input type="radio" name="${widget_name}" id="${field_id}_${value}" value="${value}" py:attrs="attrs" />
            ${desc}
        </label>
    </div>
    """

    def __init__(self, *args, **kw):
        self.validator = validators.NotEmpty()
        super(AckPanel, self).__init__(*args, **kw)

    def display(self, value=None, *args, **params):
        rs_id = value
        rs = model.RecipeSet.by_id(rs_id)
        if not rs.is_finished():
            return
        if not rs.waived:
            the_opts = [('1', 'Ack', {'checked': 1}), ('2', 'Nak', {})]
        else:
            the_opts = [('1', 'Ack', {}), ('2', 'Nak', {'checked': 1})]
        params['widget_name'] = 'response_box_%s' % rs_id
        params['options'] = the_opts
        return super(AckPanel, self).display(value, *args, **params)

class JobMatrixReport(Form):     
    javascript = [LocalJSLink('bkr','/static/javascript/jquery-ui-1.9.2.min.js', order=3),
                  LocalJSLink('bkr', '/static/javascript/job_matrix_v2.js')]
    css = [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css'),]
    template = 'bkr.server.templates.job_matrix' 
    member_widgets = ['whiteboard','job_ids','generate_button','nack_list', 'whiteboard_filter',
        'whiteboard_filter_button']
    params = (['list', 'whiteboard_options','job_ids_vals',
        'nacks','comments_field','toggle_nacks_on'])
    default_validator = validators.NotEmpty() 
    def __init__(self,*args,**kw):
        super(JobMatrixReport,self).__init__(*args, **kw)
        self.class_name = self.__class__.__name__
        self.nack_list = CheckBoxList("Hide waived",validator=self.default_validator)
        self.whiteboard = MultipleSelectField('whiteboard', label='Whiteboard', attrs={'size':5, 'class':'whiteboard'}, validator=self.default_validator)
        self.job_ids = TextArea('job_ids',label='Job ID', rows=7,cols=7, validator=self.default_validator)
        self.whiteboard_filter = TextField('whiteboard_filter', label='Filter by')
        self.whiteboard_filter_button = MyButton(name='do_filter', type='button')
        self.name='remote_form'
        self.action = '.'

    def display(self,**params):
        if 'options' in params:
            if 'whiteboard_options' in params['options']:
                params['whiteboard_options'] = params['options']['whiteboard_options']
            else:
                params['whiteboard_options'] = []

            if 'job_ids_vals' in params['options']:
                params['job_ids_vals'] = params['options']['job_ids_vals']
            if 'grid' in params['options']:
                params['grid'] = params['options']['grid']
            if 'list' in params['options']:
                params['list'] = params['options']['list']
            if 'nacks' in params['options']:
                params['nacks'] = params['options']['nacks']
            if 'toggle_nacks_on' in params['options']:
                params['toggle_nacks_on'] = params['options']['toggle_nacks_on']

        return super(JobMatrixReport,self).display(**params)

class SearchBar(RepeatingFormField):
    """Search Bar""" 
    css = [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    javascript = [LocalJSLink('bkr', '/static/javascript/search_object.js'),
                  LocalJSLink('bkr', '/static/javascript/searchbar_v11.js'),
                  LocalJSLink('bkr','/static/javascript/jquery-ui-1.9.2.min.js', order=3),]
    template = "bkr.server.templates.search_bar"

    params = ['repetitions', 'search_object', 'form_attrs', 'search_controller',
              'simplesearch','quickly_searches',
              'advanced', 'simple',
              'extra_hiddens',
              'extra_callbacks_stringified', 'table_search_controllers',
              'table_search_controllers_stringified', 'quick_searches',
              'simplesearch_label', 'result_columns','col_options',
              'col_defaults','enable_custom_columns','default_result_columns', 
              'date_picker']

    form_attrs = {}
    simplesearch = None

    def __init__(self, table, search_controller=None, extra_selects=None,
            extra_inputs=None, extra_hiddens=None, enable_custom_columns=False,
            *args, **kw):
        super(SearchBar,self).__init__(*args, **kw)
        self.enable_custom_columns = enable_custom_columns
        self.search_controller=search_controller
        self.repetitions = 1
        self.extra_hiddens = extra_hiddens
        self.default_result_columns = {}
        table_field = SingleSelectFieldJSON(name="table",
                options=sorted(table.keys()),
                validator=validators.NotEmpty())
        operation_field = SingleSelectFieldJSON(name="operation", options=[None], validator=validators.NotEmpty())
        value_field = TextFieldJSON(name="value")

        self.fields = [table_field, operation_field, value_field]
        new_selects = []
        self.extra_callbacks = {} 
        self.search_object = jsonify_for_html(table)
            
        if extra_selects is not None: 
            new_class = [] 
            for elem in extra_selects:
                if elem.has_key('display'):
                    if elem['display'] == 'none':
                        new_class.append('hide_parent')
                callback = elem.get('callback',None)
                if callback:
                    self.extra_callbacks[elem['name']] = callback 
                new_select = SingleSelectFieldJSON(name=elem['name'],options=[None], css_classes = new_class, validator=validators.NotEmpty(),for_column=elem['column'] )
                if elem['name'] == 'keyvalue':
                    self.keyvaluevalue = new_select
 
                if elem.has_key('pos'):
                    self.fields.insert(elem['pos'] - 1,new_select)
                else:
                    self.fields.append(new_select) 

        new_inputs = []
        if extra_inputs is not None:
            for the_name in extra_inputs:
                new_input = TextField(name=the_name,display='none')
                new_inputs.append(new_input) 

        if 'simplesearch_label' in kw:
            self.simplesearch_label = kw['simplesearch_label']
        else:
            self.simplesearch_label = 'Search'

        self.quickly_searches = []
        if 'quick_searches' in kw:
            if kw['quick_searches'] is not None: 
                for elem,name in kw['quick_searches']:
                    vals = elem.split('-')
                    if len(vals) != 3:
                        log.error('Quick searches expects vals as <column>-<operation>-<value>. The following is incorrect: %s' % (elem)) 
                    else: 
                        self.quickly_searches.append((name, '%s-%s-%s' % (vals[0],vals[1],vals[2])))
        self.date_picker = jsonify_for_html(kw.get('date_picker',list()) )
        controllers = kw.get('table_search_controllers',dict())  
        self.table_search_controllers_stringified = str(controllers)
        self.extra_callbacks_stringified = str(self.extra_callbacks)
        self.fields.extend(new_inputs)
        self.fields.extend(new_selects) 
 
    def display(self, value=None, **params): 
        if 'options' in params: 
            if 'columns' in params['options']:
                params['columns'] = params['options']['columns']
            if 'simplesearch' in params['options']:
                params['simplesearch'] = params['options']['simplesearch']     
            if 'result_columns' in params['options']:
                json_this = {} 
                for elem in params['options']['result_columns']: 
                    json_this.update({elem : 1})
                params['default_result_columns'] = jsonify_for_html(json_this)
            else:
                params['default_result_columns'] = 'null'
            if 'col_options' in params['options']:
                params['col_options'] = params['options']['col_options']
            else:
                params['col_options'] = []
            if 'col_defaults' in params['options']:
                params['col_defaults'] = params['options']['col_defaults']
            if 'enable_custom_columns' in params['options']:
                params['enable_custom_columns'] = params['options']['enable_custom_columns']
            if 'extra_hiddens' in params['options']:
                params['extra_hiddens'] = [(k,v) for k,v in params['options']['extra_hiddens'].iteritems()] 

        if value and not 'simplesearch' in params:
            params['advanced'] = 'True'
            params['simple'] = 'none'
        elif value and params['simplesearch'] is None: 
            params['advanced'] = 'True'
            params['simple'] = 'none'
        else:  
            params['advanced'] = 'none'
            params['simple'] = 'True'
        if value and isinstance(value, list) and len(value) > 1:
            params['repetitions'] = len(value)
        return super(SearchBar, self).display(value, **params)

    def update_params(self, d):
        super(SearchBar, self).update_params(d)
        d['button_widget'] = MyButton(name='quick_search')

class ProvisionForm(RepeatingFormField):
    pass

class TaskSearchForm(RemoteForm): 
    template = "bkr.server.templates.task_search_form"
    params = ['options','hidden']
    fields = [HiddenField(name='system_id', validator=validators.Int()),
              HiddenField(name='distro_id', validator=validators.Int()),
              HiddenField(name='distro_tree_id', validator=validators.Int()),
              HiddenField(name='task_id', validator=validators.Int()),
              TextField(name='task', label=_(u'Task')),
              TextField(name='version', label=_(u'Version')),
              TextField(name='system', label=_(u'System')),
              SingleSelectField(name='arch_id', label=_(u'Arch'),validator=validators.Int(),
                                options=model.Arch.get_all),
              TextField(name='distro', label=_(u'Distro')),
              TextField(name='whiteboard', label=_(u'Recipe Whiteboard')),
              SingleSelectField(name='osmajor_id', label=_(u'Family'),validator=validators.Int(),
                                options=lambda: [(0, 'All')] + [(m.id, m.osmajor) for m
                                    in model.OSMajor.ordered_by_osmajor(model.OSMajor.used_by_any_recipe())]),
              SingleSelectField(name='status', label=_(u'Status'), validator=ValidEnumValue(model.TaskStatus),
                                options=lambda: [(None, 'All')] + [(status, status.value) for status in model.TaskStatus]),
              SingleSelectField(name='result', label=_(u'Result'), validator=ValidEnumValue(model.TaskResult),
                                options=lambda: [(None, 'All')] + [(result, result.value) for result in model.TaskResult]),
             ]
    before = 'task_search_before()'
    on_complete = 'task_search_complete()'
    submit_text = _(u'Submit Query')

    def __init__(self, *args, **kw):
        super(TaskSearchForm,self).__init__(*args,**kw)
        self.javascript.extend([LocalJSLink('bkr', '/static/javascript/loader_v2.js')])

    def update_params(self, d):
        super(TaskSearchForm, self).update_params(d)
        if 'arch_id' in d['options']:
            d['arch_id'] = d['options']['arch_id']

class LabInfoForm(HorizontalForm):
    fields = [
        HiddenField(name="id"),
        HiddenField(name="labinfo"),
        TextField(name='orig_cost', label=_(u'Original Cost'),
            validator=validators.Money()),
        TextField(name='curr_cost', label=_(u'Current Cost'),
            validator=validators.Money()),
        TextField(name='dimensions', label=_(u'Dimensions')),
        TextField(name='weight', label=_(u'Weight'),
            validator=validators.Int()),
        TextField(name='wattage', label=_(u'Wattage'),
            validator=validators.Int()),
        TextField(name='cooling', label=_(u'Cooling'),
            validator=validators.Int()),
    ]
    submit_text = _(u'Save Lab Info Changes')

    def update_params(self, d):
        super(LabInfoForm, self).update_params(d)
        if 'labinfo' in d['value']:
            if d['value']['labinfo']:
                labinfo = d['value']['labinfo']
                d['value']['orig_cost'] = labinfo.orig_cost
                d['value']['curr_cost'] = labinfo.curr_cost
                d['value']['dimensions'] = labinfo.dimensions
                d['value']['weight'] = labinfo.weight
                d['value']['wattage'] = labinfo.wattage
                d['value']['cooling'] = labinfo.cooling

class ExcludedFamilies(FormField):
    template = """
    <div xmlns:py="http://purl.org/kid/ns#"
         class="${field_class}"
         id="${field_id}"
     >
        <div class="filter">
            <strong>Filter by OS family:</strong>
            <input
                placeholder="Type here to apply filter"
                onkeyup="filterFamilies(event.target.value)"
                onkeydown="preventSubmit(event)"
            />
        </div>
        <p><strong>Available architectures:</strong></p>
        <ul class="nav nav-tabs available-archs" role="tablist">
            <li py:for="arch, _ in options">
                <a href="#arch-${arch}"
                    class="nav-link"
                    id="${arch}-tab"
                    data-toggle="tab"
                >
                    ${arch}
                </a>
            </li>
        </ul>
        <div class="tab-content archs-list">
            <div id="arch-${arch}" class="tab-pane fade" py:for="arch, a_options in options">
                <div class="arch-title excluded-families-title">
                    <span>Architecture: ${arch}</span>
                    <button type="button"
                        class="btn"
                        onclick="toggleExclude('${arch}')"
                    >
                        Toggle ${arch}
                    </button>
                </div>
                <div class="category-list" py:for="category, cat_options in a_options">
                    <div class="category-title excluded-families-title">
                        <span>${category}</span>
                        <button type="button"
                            class="btn"
                            onclick="toggleExclude('${arch}','${category}')"
                        >
                            Toggle
                        </button>
                    </div>
                    <div py:for="value, desc, subsection, attrs in cat_options">
                        <label class="with-arrow">
                            <input class="majorCheckbox"
                                type="checkbox"
                                name="${name}.${arch}"
                                id="${field_id}_${value}_${arch}_${category}"
                                value="${value}"
                                py:attrs="attrs"
                                onchange="checkMajor(this)"
                            />
                            <span>${desc}</span>
                        </label>
                        <i class="fa fa-angle-down" data-toggle="collapse" data-target="#collapse-${arch}-${desc}"></i>
                        <ul class="collapse os-version-list"
                            id="collapse-${arch}-${desc}"
                        >
                            <li py:for="subvalue, subdesc, attrs  in subsection">
                                <label>
                                    <input type="checkbox"
                                        name="${name}_subsection.${arch}"
                                        id="${field_id}_${value}_sub_${subvalue}_${arch}"
                                        value="${subvalue}"
                                        py:attrs="attrs"
                                        onchange="checkVersion(this)"
                                    />
                                    <span>${subdesc}</span>
                                </label>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        <div class="back-to-top">
            <button type="button"
                onclick="backToTop()"
            >
                Back to Top
                <i class="fa fa-arrow-up"></i>
            </button>
        </div>
        <script>
            initializeExcludedFamilies();
        </script>
     </div>
    """


    _multiple_selection = True
    _selected_verb = 'checked'
    _major_categories = [
        {
            'name': 'RHEL',
            'match': 'RedHatEnterprise'
        },{
            'name': 'Fedora',
            'match':  'Fedora'
        }
    ]
    params = ["attrs", "options", "list_attrs"]
    params_doc = {'list_attrs' : 'Extra (X)HTML attributes for the ul tag'}
    list_attrs = {}
    attrs = {}
    options = []

    def __init__(self, *args, **kw):
        super(ExcludedFamilies, self).__init__(*args, **kw)

    def update_params(self, d):

        super(ExcludedFamilies, self).update_params(d)
        a_options = []
        for arch,arch_options in d["options"]:
            options = { name: [] for name in [category['name'] for category in self._major_categories]}
            options['Other'] = []
            for option in arch_options:
                soptions = []
                option_attrs = dict(option[3]) if len(option) == 4 else {}
                if d['attrs'].has_key('readonly'):
                    option_attrs['readonly'] = 'readonly'
                if self._is_selected(option[0], d['value'][0][arch]):
                    option_attrs[self._selected_verb] = self._selected_verb
                for soption in option[2]:
                    soption_attrs = dict(soption[2]) if len(soption) == 3 else {}
                    if d['attrs'].has_key('readonly'):
                        soption_attrs['readonly'] = 'readonly'
                    if self._is_selected(soption[0], d['value'][1][arch]):
                        soption_attrs[self._selected_verb] = self._selected_verb
                    soptions.append((soption[0], soption[1], soption_attrs))
                option_category = 'Other'
                for category in self._major_categories:
                    if option[1].find(category['match']) == 0:
                        option_category = category['name']
                options[option_category].append((option[0], option[1], soptions, option_attrs))
            for category in options:
                options[category].sort(key=lambda o: o[1])
            ordered_categories = []
            for category in self._major_categories:
                ordered_categories.append((category['name'], options[category['name']]))
            ordered_categories.append(('Other', options['Other']))
            a_options.append((arch, ordered_categories))
        d["options"] = a_options

    def _is_selected(self, option_value, value):
        if value is not None:
            if self._multiple_selection:
                if option_value in value:
                    return True
            else:
                if option_value == value:
                    return True
        return False

class SystemKeys(Form):
    template = "bkr.server.templates.system_keys"
    member_widgets = ["id", "key_name", "key_value", "delete_link"]
    params = ['options', 'readonly', 'key_values_int', 'key_values_string']
    delete_link = DeleteLinkWidgetForm()

    def __init__(self, *args, **kw):
        super(SystemKeys, self).__init__(*args, **kw)
        self.id = HiddenField(name="id")
        self.key_name = TextField(name='key_name', label=_(u'Key'))
        self.key_value = TextField(name='key_value', label=_(u'Value'))

    def update_params(self, d):
        super(SystemKeys, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        d['key_values'] = sorted(chain(
                d['options'].get('key_values_int', []), 
                d['options'].get('key_values_string', [])),
                key=lambda kv: (kv.key.key_name, kv.key_value))

class DistroTags(Form):
    template = "bkr.server.templates.distro_tags"
    member_widgets = ["id", "tag", "delete_link"]
    javascript = [LocalJSLink('bkr', '/static/javascript/util.js'),
        LocalJSLink('bkr', '/static/javascript/magic_forms.js')]
    params = ['options', 'readonly', 'tags']

    def __init__(self, *args, **kw):
        super(DistroTags, self).__init__(*args, **kw)
        self.id    = HiddenField(name="id")
        self.delete_link = DeleteLinkWidgetForm()
        self.tag = AutoCompleteField(name='tag',
                                      search_controller="/tags/by_tag",
                                      search_param="tag",
                                      result_name="tags")

    def update_params(self, d):
        super(DistroTags, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'tags' in d['options']:
            d['tags'] = d['options']['tags']


class SystemInstallOptions(Form):
    javascript = [LocalJSLink('bkr', '/static/javascript/install_options.js')]
    template = "bkr.server.templates.system_installoptions"
    member_widgets = ["id", "prov_arch", "prov_osmajor", "prov_osversion",
                       "prov_ksmeta", "prov_koptions", "prov_koptionspost", "delete_link"]
    params = ['options', 'readonly', 'provisions']
    delete_link = DeleteLinkWidgetForm()

    
    def __init__(self, *args, **kw):
        super(SystemInstallOptions, self).__init__(*args, **kw)
        self.id                = HiddenField(name="id")
        self.prov_arch         = SingleSelectField(name='prov_arch',
                                 label=_(u'Arch'),
                                 options=[],
                                 validator=validators.NotEmpty())
        self.prov_osmajor      = SingleSelectField(name='prov_osmajor',
                                 label=_(u'Family'),
                                 options=lambda: [(0, 'All')] +
                                    [(m.id, m.osmajor) for m in model.OSMajor.ordered_by_osmajor()],
                                 validator=validators.NotEmpty())
        self.prov_osversion    = SingleSelectField(name='prov_osversion',
                                 label=_(u'Update'),
                                 options=[(0,u'All')],
                                 validator=validators.NotEmpty())
        self.prov_ksmeta       = TextField(name='prov_ksmeta', 
                                     label=_(u'Kickstart Metadata'))
        self.prov_koptions     = TextField(name='prov_koptions', 
                                       label=_(u'Kernel Options'))
        self.prov_koptionspost = TextField(name='prov_koptionspost',
                                           label=_(u'Kernel Options Post'))

    def update_params(self, d):
        super(SystemInstallOptions, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'provisions' in d['options']:
            d['provisions'] = d['options']['provisions']

class SystemExclude(Form):
    template = """
    <form xmlns:py="http://purl.org/kid/ns#"
          name="${name}"
          action="${action}"
          method="post" width="100%">
        <button id="excludeButton" type="button" py:if="not readonly" class="btn" onclick='toggleExcludeAll();'><strong>Toggle All Architectures/Families</strong></button>
        <a py:if="not readonly" class="btn btn-primary" href="javascript:document.${name}.submit();">Save Exclude Changes</a>
        ${display_field_for("id")}
        ${display_field_for("excluded_families")}
    </form>
    """
    member_widgets = ["id", "excluded_families"]
    params = ['options', 'readonly']
    params_doc = {}

    def __init__(self, *args, **kw):
        super(SystemExclude, self).__init__(*args, **kw)
        self.id = HiddenField(name="id")
        self.excluded_families = ExcludedFamilies(name="excluded_families")

    def update_params(self, d):
        super(SystemExclude, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']

class SystemDetails(Widget):
    template = "bkr.server.templates.system_details"
    params = ['system']

class TasksWidget(CompoundWidget):
    template = "bkr.server.templates.tasks_widget"
    params = ['tasks', 'hidden','action']
    member_widgets = ['link']
    action = '/tasks/do_search'
    link = LinkRemoteFunction(name='link', before='task_search_before()', on_complete='task_search_complete()')


class RecipeSetWidget(CompoundWidget):
    javascript = []
    css = []
    template = "bkr.server.templates.recipe_set"
    params = ['recipeset','show_priority','action','priorities_list', 'can_ack_nak']
    member_widgets = ['priority_widget','retentiontag_widget', 'ack_panel_widget', 'product_widget', 'action_widget']
    def __init__(self, priorities_list=None, *args, **kw):
        self.action_widget = RecipeTaskActionWidget()
        self.priorities_list = priorities_list
        self.ack_panel_widget = AckPanel()
        self.priority_widget = PriorityWidget()
        self.retentiontag_widget = RetentionTagWidget()
        if 'recipeset' in kw:
            self.recipeset = kw['recipeset']
        else:
            self.recipeset = None

    def update_params(self, d):
        super(RecipeSetWidget,self).update_params(d)
        recipeset = d['recipeset']
        owner_groups = [g.group_name for g in recipeset.job.owner.groups]
        user = identity.current.user
        if recipeset.can_waive(user):
            can_ack_nak = True
        else:
            #Can't ack if we don't fulfil these requirements
            can_ack_nak = False
        d['can_ack_nak'] = can_ack_nak


class RecipeTaskActionWidget(RPC):
    template = 'bkr.server.templates.action'
    """
    RecipeTaskActionWidget will display the appropriate actions for a task
    """
    def __init__(self, *args, **kw):
        super(RecipeTaskActionWidget,self).__init__(*args, **kw)
    
    def display(self, task, *args, **params): 
        params['task'] = task
        return super(RecipeTaskActionWidget, self).display(*args, **params)


class ReportProblemForm(RemoteForm):
    template = 'bkr.server.templates.report_problem_form'
    fields=[
        TextArea(name='description', label='Description of problem',
            validator=validators.NotEmpty())]
    desc = 'Report Problem'
    submit = Button(name='submit')
    submit_text = 'Report'
    member_widgets = ['submit']
    params = ['system', 'recipe']
    name = 'problem'
    on_success = 'success(\'Your problem has been reported, Thank you\')'
    on_failure = 'failure(\'We were unable to report your problem at this time\')'
 
    def update_params(self, d):
        super(ReportProblemForm, self).update_params(d)
        d['system'] = d['options']['system']
        d['recipe'] = d['options'].get('recipe')
        d['hidden_fields'] = []
        d['hidden_fields'].append(HiddenField(name='system', attrs= {'value' : d['system'] }))
        if d['recipe']:
            d['hidden_fields'].append(HiddenField(name='recipe_id', attrs={'value' : d['recipe'].id}))
        d['submit'].attrs.update({'onClick' :  "return ! system_action_remote_form_request('%s', %s, '%s');" % (
            d['options']['name'], jsonify_for_html(self.get_options(d)), d['action'])})


class RecipeActionWidget(CompoundWidget):
    template = 'bkr.server.templates.recipe_action'
    javascript = [LocalJSLink('bkr', '/static/javascript/util.js'),
        LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),]
    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    problem_form = ReportProblemForm()
    report_problem_options = {}
    params = ['report_problem_options', 'recipe_status_reserved']
    member_widgets = ['problem_form']

    def __init__(self, *args, **kw):
        super(RecipeActionWidget, self).__init__(*args, **kw)

    def display(self, task, **params):
        if getattr(task.resource, 'system', None):
            params['report_problem_options'] = {'system' : task.resource.system,
                'recipe' : task, 'name' : 'report_problem_recipe_%s' % task.id,
                'action' : '../system_action/report_system_problem'}
        return super(RecipeActionWidget,self).display(task, **params)

    def update_params(self, d):
        super(RecipeActionWidget, self).update_params(d)
        d['recipe_status_reserved'] = TaskStatus.reserved

class RecipeWidget(CompoundWidget):
    css = []
    template = "bkr.server.templates.recipe_widget"
    params = ['recipe', 'recipe_systems', 'recipe_status_reserved']
    member_widgets = ['action_widget']
    action_widget = RecipeActionWidget()

    def update_params(self, d):
        super(RecipeWidget, self).update_params(d)
        d['recipe_systems'] = \
            make_link(url('../recipes/systems?recipe_id=%d' % d['recipe'].id),
                      d['recipe'].dyn_systems.count())
        d['recipe_status_reserved'] = TaskStatus.reserved

class ProductWidget(SingleSelectField, RPC):
    javascript = [LocalJSLink('bkr', '/static/javascript/job_product.js')]
    validator = validators.NotEmpty()
    params = ['action', 'job_id']
    action  = '/jobs/update'
    before = 'job_product_before()'
    on_complete = 'job_product_complete()'
    on_success = 'job_product_save_success()'
    on_failure = 'job_product_save_failure()'
    validator = validators.NotEmpty()
    product_deselected = 0

    def __init__(self, *args, **kw):
       self.options = []
       self.field_class = 'singleselectfield'

    def display(self,value=None, *args, **params):
        params['options'] =[(self.product_deselected, 'No Product')] + \
            [(elem.id,elem.name) for elem in model.Product.query.order_by(model.Product.name).all()]
        return super(ProductWidget,self).display(value,**params)

    def update_params(self, d):
        super(ProductWidget, self).update_params(d)
        d['attrs']['id'] = 'job_product'
        d['attrs']['class'] = 'input-block-level'
        d['attrs']['onchange'] = "ProductChange('%s',%s, %s)" % (
            url(d.get('action')),
            jsonify_for_html({'id': d.get('job_id')}),
            jsonify_for_html(self.get_options(d)),
            )

class RetentionTagWidget(SingleSelectField, RPC): #FIXME perhaps I shoudl create a parent that both Retention and Priority inherit from
    javascript = [LocalJSLink('bkr', '/static/javascript/job_retentiontag.js')]
    validator = validators.NotEmpty()
    params = ['action', 'job_id']
    action  = '/jobs/update'
    before = 'job_retentiontag_before()'
    on_complete = 'job_retentiontag_complete()'
    on_success = 'job_retentiontag_save_success()'
    on_failure = 'job_retentiontag_save_failure()'

    def __init__(self, *args, **kw):
       self.options = []
       self.field_class = 'singleselectfield'

    def display(self,value=None, **params):
        params['options'] = [(elem.id,elem.tag) for elem in model.RetentionTag.query.all()]
        return super(RetentionTagWidget,self).display(value, **params)

    def update_params(self, d):
        super(RetentionTagWidget, self).update_params(d)
        d['attrs']['id'] = 'job_retentiontag'
        d['attrs']['onchange'] = "RetentionTagChange('%s',%s, %s)" % (
            url(d.get('action')),
            jsonify_for_html({'id': d.get('job_id')}),
            jsonify_for_html(self.get_options(d)),
            )


class PriorityWidget(SingleSelectField):   
   validator = ValidEnumValue(model.TaskPriority)
   params = ['default','controller'] 
   def __init__(self,*args,**kw): 
       self.options = [] 
       self.field_class = 'singleselectfield' 

   def display(self,obj,value=None,**params):           
       if 'priorities' in params: 
           params['options'] = [(pri, pri.value) for pri in params['priorities']]
       else:
           params['options'] = [(pri, pri.value) for pri in model.TaskPriority]
       if isinstance(obj,model.Job):
           if 'id_prefix' in params:
               params['attrs'] = {'id' : '%s_%s' % (params['id_prefix'],obj.id) }
       elif obj:
           if 'id_prefix' in params:
               params['attrs'] = {'id' : '%s_%s' % (params['id_prefix'],obj.id) } 
           value = obj.priority
       return super(PriorityWidget,self).display(value or None,**params)

class AlphaNavBar(Widget):
    template = "bkr.server.templates.alpha_navbar"
    params = ['letters','keyword']

    def __init__(self,letters,keyword='alpha',*args,**kw):
        self.letters = letters 
        self.keyword = keyword


class JobWhiteboard(RPC, CompoundWidget):
    """
    Widget for displaying/updating a job's whiteboard. Saves asynchronously using js.
    """

    template = 'bkr.server.templates.job_whiteboard'
    hidden_id = HiddenField(name='id')
    field = TextField(name='whiteboard')
    member_widgets = ['hidden_id', 'field']
    params = ['action', 'form_attrs', 'job_id', 'readonly']
    params_doc = {'action': 'Form action (URL to submit to)',
                  'form_attrs': 'Additional HTML attributes to set on the <form>',
                  'job_id': 'Job id whose whiteboard is being displayed in this widget',
                  'readonly': 'Whether changes to the whiteboard are forbidden'}
    action = '/jobs/update'
    form_attrs = {}
    readonly = False
    # these are references to js functions defined in the widget template:
    before = 'job_whiteboard_before()'
    on_complete = 'job_whiteboard_complete()'
    on_success = 'job_whiteboard_save_success()'
    on_failure = 'job_whiteboard_save_failure()'

    # taken from turbogears.widgets.RemoteForm
    def update_params(self, d):
        super(JobWhiteboard, self).update_params(d)
        d['form_attrs']['onsubmit'] = "return !remoteFormRequest(this, null, %s);" % (
            jsonify_for_html(self.get_options(d)))


class TaskActionWidget(RPC):
    template = 'bkr.server.templates.task_action'
    params = ['redirect_to']
    action = url('/tasks/disable_from_ui')
    javascript = [LocalJSLink('bkr', '/static/javascript/task_disable.js')]

    def __init__(self, *args, **kw):
        super(TaskActionWidget, self).__init__(*args, **kw)

    def display(self, task, action=None, **params):
        id = task.id
        task_details={'id': 'disable_%s' % id,
            't_id' : id}
        params['task_details'] = task_details
        if action:
            params['action'] = action
        return super(TaskActionWidget, self).display(task, **params)

    def update_params(self, d):
        super(TaskActionWidget, self).update_params(d)
        d['task_details']['onclick'] = "TaskDisable('%s',%s, %s); return false;" % (
            d.get('action'),
            jsonify_for_html({'t_id': d['task_details'].get('t_id')}),
            jsonify_for_html(self.get_options(d)),
            )

class JobActionWidget(CompoundWidget):
    template = 'bkr.server.templates.job_action'
    params = ['redirect_to', 'job_delete_attrs']
    member_widgets = ['delete_link']
    javascript = [LocalJSLink('bkr', '/static/javascript/job_row_delete.js')]
    delete_link = DeleteLinkWidgetAJAX()

    def display(self, task, **params):
        t_id = task.t_id
        job_details = {'id': 'delete_%s' % t_id,
                       't_id' : t_id,
                       'class' : 'list'}
        params['job_details'] = job_details
        if 'export' not in params:
            params['export'] = None

        job_data = {'t_id' : params['job_details'].get('t_id')}
        params['job_delete_attrs'] = {'data' : job_data,
                                      'action' : params['delete_action'],
                                      'callback' : 'job_delete_success',
                                      'show_icon': False}
        return super(JobActionWidget, self).display(task, **params)


class JobPageActionWidget(JobActionWidget):
    params = []
    javascript = [LocalJSLink('bkr', '/static/javascript/job_page_delete.js'),
        LocalJSLink('bkr', '/static/javascript/util.js')]
    delete_link = DeleteLinkWidgetForm()

    def update_params(self, d):
        super(JobPageActionWidget, self).update_params(d)
        value = {'t_id' : d['job_details'].get('t_id') }
        d['job_delete_attrs'] = { 'value' : value,
                                  'show_icon': False,
                                  'action' : d['job_delete_attrs'].get('action') }


class DistroTreeInstallOptionsWidget(Widget):
    template = 'bkr.server.templates.distrotree_install_options'
    params = ['readonly']
