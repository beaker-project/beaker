from turbogears import validators, url, config
from kid import Element
import time
import turbogears as tg
from turbojson import jsonify
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
                                HiddenField, RemoteForm, LinkRemoteFunction, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, DataGrid, RepeatingFormField,
                                CompoundWidget, AjaxGrid, CSSLink,
                                MultipleSelectField, Button,
                                RepeatingFieldSet, SelectionField, WidgetsList,
                                PasswordField)

from bkr.server import model, search_utility, identity
from bkr.server.assets import get_assets_env
from bkr.server.bexceptions import BeakerException
from bkr.server.helpers import make_link
from bkr.server.validators import UniqueLabControllerEmail
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
        super(JSLink, self).update_params(d)
        d["link"] = url(self.name)


class LocalCSSLink(CSSLink):
    """
    Link to local CSS files
    """
    def update_params(self, d):
        super(CSSLink, self).update_params(d)
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
            d.get("update", ''), jsonify.encode(self.get_options(d)))


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
              <i class="icon-remove" py:if="show_icon"/> ${action_text}
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
            <i class="icon-remove" py:if="show_icon"/> ${action_text}
        </a>"""
    params = ['data', 'callback', 'action_type']

    def display(self, value=None, **params):
        missing = [(i, True) for i in ['action', 'data', 'callback']
                      if not params.get(i)]
        if any(missing):
            raise ValueError('Missing arguments to %s: %s' %
                (self.__class__.__name__, ','.join(dict(missing).keys())))
        params['action_type'] = params.get('action_type', 'delete')
        params['data'] = jsonify.encode(params['data'])
        return super(DeleteLinkWidgetAJAX, self).display(value, **params)


class GroupPermissions(Widget):

    javascript = [LocalJSLink('bkr', '/static/javascript/group_permission_v4.js'),
        LocalJSLink('bkr', '/static/javascript/util.js'),
        LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),]
    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    member_widgets = ['form', 'grid']
    template = """
        <div xmlns:py="http://purl.org/kid/ns#">
            <script type='text/javascript'>
                var permissions_form_id = "${form.name}"
                 var permissions_grid_id = "${grid.name}"
                 var group_id = "${value.group_id}"
            </script>
            ${grid.display(value.permissions)}
            <div py:if="tg.identity.user and tg.identity.user.is_admin()"
                 py:content="form.display(action='./save_group_permissions', value=value)" />
        </div>
        """

class ReserveSystem(HorizontalForm):
    fields = [ 
          HiddenField(name='system_id'),
              Label(name='system', label=_(u'System to Provision')),
              Label(name='distro', label=_(u'Distro Tree to Provision')),
              TextField(name='whiteboard', attrs=dict(size=50),
                        label=_(u'Job Whiteboard')),
              TextField(name='ks_meta', attrs=dict(size=50),
                        label=_(u'KickStart MetaData')),
              TextField(name='koptions', attrs=dict(size=50),
                        label=_(u'Kernel Options (Install)')),
              TextField(name='koptions_post', 
                        attrs=dict(size=50),
                        label=_(u'Kernel Options (Post)')),
             ]
    submit_text = 'Queue Job'

    def update_params(self,d): 
        log.debug(d)
        if 'value' in d:
            if 'distro_tree_ids' in d['value']:
                if(isinstance(d['value']['distro_tree_ids'],list)):
                    for distro_tree_id in d['value']['distro_tree_ids']:
                        d['hidden_fields'] = [HiddenField(name='distro_tree_id', attrs={'value' : distro_tree_id})] + d['hidden_fields'][0:]
                

        super(ReserveSystem,self).update_params(d)


class ReserveWorkflow(Form): 
    javascript = [LocalJSLink('bkr', '/static/javascript/loader_v2.js'),
                  LocalJSLink('bkr', '/static/javascript/reserve_workflow_v8.js'),
                 ] 
    template="bkr.server.templates.reserve_workflow"
    fields = [
        SingleSelectField(name='osmajor', label=_(u'Family'),
            validator=validators.UnicodeString(),
            css_classes=['distro_filter_criterion']),
        SingleSelectField(name='tag', label=_(u'Tag'),
            validator=validators.UnicodeString(),
            css_classes=['distro_filter_criterion']),
        SingleSelectField(name='distro', label=_(u'Distro'),
            validator=validators.UnicodeString(),
            css_classes=['distro_tree_filter_criterion']),
        SingleSelectField(name='lab_controller_id', label=_(u'Lab'),
            validator=validators.Int(),
            css_classes=['distro_tree_filter_criterion']),
        MultipleSelectField(name='distro_tree_id', label=_(u'Distro Tree'),
                size=7, validator=validators.Int()),
    ]
    params = ['get_distros_rpc', 'get_distro_trees_rpc']


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
    params = ['add_action']

class LabControllerDataGrid(myPaginateDataGrid):
    javascript = [LocalJSLink('bkr','/static/javascript/lab_controller_remove.js'),
                  LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),]
    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]

class SingleSelectFieldJSON(SingleSelectField):
    params = ['for_column']
    def __init__(self,*args,**kw):
        super(SingleSelectField,self).__init__(*args,**kw)

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
    def __init__(self,*args,**kw):
        super(TextField,self).__init__(*args,**kw)
    def __json__(self):
        return {
                'field_id' : self.field_id,             
               }


class LabControllerFormSchema(validators.Schema):
    fqdn = validators.UnicodeString(not_empty=True, max=256, strip=True)
    lusername = validators.UnicodeString(not_empty=True)
    email = validators.Email(not_empty=True)
    chained_validators = [UniqueLabControllerEmail('id', 'email', 'lusername')]


class LabControllerForm(HorizontalForm):
    action = 'save_data'
    submit_text = _(u'Save')
    fields = [
              HiddenField(name='id'),
              TextField(name='fqdn', label=_(u'FQDN')),
              TextField(name='lusername',
                       label=_(u'Username')),
              PasswordField(name='lpassword',
                            label=_(u'Password')),
              TextField(name='email', 
                        label=_(u'Lab Controller Email Address')),
              CheckBox(name='disabled',
                       label=_(u'Disabled'),
                       default=False),
             ]
    validator = LabControllerFormSchema()

    def update_params(self, d):
        super(LabControllerForm, self).update_params(d)
        if 'user' in d['options']:
            d['value']['lusername'] = d['options']['user'].user_name
            d['value']['email'] = d['options']['user'].email_address
            

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
                  LocalJSLink('bkr','/static/javascript/response_v4.js')]

    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    params = ['widget_name','unreal_response','comment_id','comment_class']
    template = """
    <div xmlns:py="http://purl.org/kid/ns#"
        class="${field_class}"
        id="${field_id}"
    >
        <label py:for="value, desc, attrs in options" class="radio">
            <input type="radio" name="${widget_name}" py:if="unreal_response != value" id="${field_id}_${value}" value="${value}" py:attrs="attrs" />
            <input type="radio" name="${widget_name}" py:if="unreal_response == value" id="unreal_response" value="${value}" py:attrs="attrs" />
            ${desc}
        </label>
        <a id="${comment_id}" class="${comment_class}" style="cursor:pointer;display:inline-block;margin-top:0.3em">comment</a>
    </div>
    """
    
    def __init__(self,*args,**kw):
        #self.options = options 
        self.validator = validators.NotEmpty() 
        super(AckPanel,self).__init__(*args,**kw)

    def display(self,value=None,*args,**params): 
        #params['options']  = self.options
        pre_ops = [(str(elem.id),elem.response.capitalize(),{}) for elem in model.Response.get_all()]
        if len(pre_ops) is 0: #no responses in the Db ? lets get out of here
            return
        OPTIONS_ID_INDEX = 0
        OPTIONS_RESPONSE_INDEX = 1
        OPTIONS_ATTR_INDEX = 2
        # Purpose of this for loops is to determine details of where the responses are in the options list
        # and how to create a non response item as well (i.e 'Needs Review')
        max_response_id = 0
        for index,(id,response,attrs) in enumerate(pre_ops):
            if response == 'Ack':
                ACK_INDEX = index
                ACK_ID = id
            elif response == 'Nak':
                NAK_INDEX = index
                NAK_ID = id 
            if id > max_response_id:
                max_response_id = int(id) + 1 #this is a number which is one bigger than our biggest valid response_id
        else: 
            EXTRA_RESPONSE_INDEX = index + 1 
        EXTRA_RESPONSE_RESPONSE = 'Needs Review' 
        pre_ops.append((max_response_id,EXTRA_RESPONSE_RESPONSE,{}))
        params['unreal_response'] = max_response_id # we use this in the template to determine which response is not a real one
        
        rs_id = value
        rs = model.RecipeSet.by_id(rs_id)
        if not rs.is_finished():
            return 
        the_opts = pre_ops

        #If not nacked
        if not rs.nacked: # We need to review 
            if not rs.is_failed(): #it's passed,
                rs.nacked = model.RecipeSetResponse(type='ack') # so we will auto ack it
                the_opts[ACK_INDEX] = (the_opts[ACK_INDEX][OPTIONS_ID_INDEX],the_opts[ACK_INDEX][OPTIONS_RESPONSE_INDEX],{'checked': 1 })
                del(the_opts[EXTRA_RESPONSE_INDEX])
            else:
                the_opts[EXTRA_RESPONSE_INDEX] = (the_opts[EXTRA_RESPONSE_INDEX][OPTIONS_ID_INDEX],the_opts[EXTRA_RESPONSE_INDEX][OPTIONS_RESPONSE_INDEX],{'checked': 1 }) 
                params['comment_class'] = 'hidden'

        else: #Let's get aout value from the db  
            if rs.nacked.response == model.Response.by_response('ack'):# We've acked it 
                the_opts[ACK_INDEX] = (the_opts[ACK_INDEX][OPTIONS_ID_INDEX],the_opts[ACK_INDEX][OPTIONS_RESPONSE_INDEX],{'checked': 1 })
                del(the_opts[EXTRA_RESPONSE_INDEX])
            elif  rs.nacked.response == model.Response.by_response('nak'): # We've naked it
                the_opts[NAK_INDEX] = (the_opts[NAK_INDEX][OPTIONS_ID_INDEX],the_opts[NAK_INDEX][OPTIONS_RESPONSE_INDEX],{'checked': 1 })
                del(the_opts[EXTRA_RESPONSE_INDEX])
        params['widget_name'] = 'response_box_%s' % rs_id 
        params['options'] = the_opts
        try:
            params['comment_id'] = "comment_%s" % (params['name'])
        except KeyError,e:
            log.debug("Unable to use name given to %s for comment id" % self.__class__.__name__)
            params['comment_id'] = "comment_%s" % rs_id
        return super(AckPanel,self).display(value,*args,**params)
 
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
        self.nack_list = CheckBoxList("Hide naks",validator=self.default_validator)
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
                  LocalJSLink('bkr', '/static/javascript/searchbar_v9.js'),
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
        complete_data=None, *args, **kw):

        super(SearchBar,self).__init__(*args, **kw)
        self.enable_custom_columns = enable_custom_columns
        self.search_controller=search_controller
        self.repetitions = 1
        self.extra_hiddens = extra_hiddens
        self.default_result_columns = {}
        table_field = SingleSelectFieldJSON(name="table", options=table, validator=validators.NotEmpty()) 
        operation_field = SingleSelectFieldJSON(name="operation", options=[None], validator=validators.NotEmpty())
        value_field = TextFieldJSON(name="value")

        self.fields = [table_field, operation_field, value_field]
        new_selects = []
        self.extra_callbacks = {} 
        self.search_object = jsonify.encode(complete_data)
            
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
        self.date_picker = jsonify.encode(kw.get('date_picker',list()) )
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
                params['default_result_columns'] = jsonify.encode(json_this)     
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

class SystemCommandsForm(Form):
    template = "bkr.server.templates.system_commands_form"
    member_widgets = ["id", "power", "lab_controller"]
    params = ['options', 'action', 'can_power', 'is_user',
              'power_enabled', 'netboot_enabled']

    def __init__(self, *args, **kw):
        super(SystemCommandsForm, self).__init__(*args, **kw)
        self.id = HiddenField(name="id")
        self.power = HiddenField(name="power")
        self.lab_controller = HiddenField(name="lab_controller")

    def display(self, value, *args, **kw):
        if 'options' in kw:
            kw.update(kw['options'])
        system = value
        kw['power_enabled'] = bool(system.power and system.lab_controller)
        kw['netboot_enabled'] = bool(system.lab_controller)
        kw['fqdn'] = system.fqdn
        return super(SystemCommandsForm, self).display(value, *args, **kw)

class PowerActionHistory(CompoundWidget):
    template = "bkr.server.templates.power_history_grid"
    member_widgets = ['grid']
    def __init__(self):
        self.grid  = BeakerDataGrid(fields = [DataGrid.Column(name='user',title='User',
                                                                          getter=lambda x: x.user),
                                                  DataGrid.Column(name='service', title='Service',
                                                                          getter=lambda x: x.service),
                                                  DataGrid.Column(name='created', title='Submitted',
                                                                          getter=lambda x: x.created,
                                                                          options=dict(datetime=True)),
                                                  DataGrid.Column(name='action', title='Action',
                                                                          getter=lambda x: x.action),
                                                  DataGrid.Column(name='status',title='Status',
                                                                          getter=lambda x: x.status),
                                                  DataGrid.Column(name='new_value',title='Message',
                                                                          getter=lambda x: x.new_value)])



class TaskSearchForm(RemoteForm): 
    template = "bkr.server.templates.task_search_form"
    params = ['options','hidden']
    fields = [HiddenField(name='system_id', validator=validators.Int()),
              HiddenField(name='distro_id', validator=validators.Int()),
              HiddenField(name='distro_tree_id', validator=validators.Int()),
              HiddenField(name='task_id', validator=validators.Int()),
              TextField(name='task', label=_(u'Task')),
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

class PowerForm(HorizontalForm):
    fields = [
        HiddenField(name="fqdn"),
        HiddenField(name="power"),
        SingleSelectField(name='power_type_id',
            label=_(u'Power Type'),
            options=model.PowerType.get_all,
            validator=validators.NotEmpty()),
        TextField(name='power_address', label=_(u'Power Address')),
        TextField(name='power_user', label=_(u'Power Login')),
        TextField(name='power_passwd', label=_(u'Power Password')),
        TextField(name='power_id', label=_(u'Power Port/Plug/etc')),
        TextField(name='power_quiescent_period', label=_(u'Quiescent Period'),
            validator=validators.Int(not_empty=True)),
        RadioButtonList(name='release_action',
            label=_(u'Release Action'),
            options=[(ra, unicode(ra)) for ra in model.ReleaseAction],
            default=model.ReleaseAction.power_off,
            validator=ValidEnumValue(model.ReleaseAction)),
        SingleSelectField(name='reprovision_distro_tree_id',
            label=_(u'Reprovision Distro'),
            options=[],
            validator=validators.Int(non_empty=True)),
    ]
    submit_text = _(u'Save Power Changes')

    def update_params(self, d):
        super(PowerForm, self).update_params(d)
        if 'power' in d['value']:
            if d['value']['power']:
                power = d['value']['power']
                d['value']['power_type_id'] = power.power_type_id
                d['value']['power_address'] = power.power_address
                d['value']['power_user'] = power.power_user
                d['value']['power_passwd'] = power.power_passwd
                d['value']['power_id'] = power.power_id
                d['value']['power_quiescent_period'] = power.power_quiescent_period


class ExcludedFamilies(FormField):
    template = """
    <ul xmlns:py="http://purl.org/kid/ns#"
        class="${field_class}"
        id="${field_id}"
        py:attrs="list_attrs"
    >
     <li py:for="arch, a_options in options">
      ${arch}
      <ul xmlns:py="http://purl.org/kid/ns#"
          class="${field_class}"
          id="${field_id}_${arch}"
          py:attrs="list_attrs"
      >
       <li py:for="value, desc, subsection, attrs in a_options">
        <label class="checkbox">
        <input type="checkbox"
               name="${name}.${arch}"
               id="${field_id}_${value}_${arch}"
               value="${value}"
               py:attrs="attrs"
        />
        ${desc}
        </label>
        <ul xmlns:py="http://purl.org/kid/ns#"
            class="${field_class}"
            id="${field_id}_${value}_sub"
            py:attrs="list_attrs"
        >
         <li py:for="subvalue, subdesc, attrs  in subsection">
          <label class="checkbox">
          <input type="checkbox"
                 name="${name}_subsection.${arch}"
                 id="${field_id}_${value}_sub_${subvalue}_${arch}"
                 value="${subvalue}"
                 py:attrs="attrs"
          />
          ${subdesc}
          </label>
         </li>
        </ul>
       </li>
      </ul>
     </li>
    </ul>
    """


    _multiple_selection = True
    _selected_verb = 'checked'
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
            options = []
            for optgroup in arch_options:
                optlist = [optgroup]
                soptions = []
                for i, option in enumerate(optlist):
                    if len(option) is 3:
                        option_attrs = {}
                    elif len(option) is 4:
                        option_attrs = dict(option[3])
                    if d['attrs'].has_key('readonly'):
                        option_attrs['readonly'] = 'True'
                    if self._is_selected(option[0], d['value'][0][arch]):
                        option_attrs[self._selected_verb] = self._selected_verb
                    for soptgroup in option[2]:
                        soptlist = [soptgroup]
                        for j, soption in enumerate(soptlist):
                            if len(soption) is 2:
                                soption_attrs = {}
                            elif len(soption) is 3:
                                soption_attrs = dict(soption[2])
                            if d['attrs'].has_key('readonly'):
                                soption_attrs['readonly'] = 'True'
                            if self._is_selected(soption[0], d['value'][1][arch]):
                                soption_attrs[self._selected_verb] = self._selected_verb
                            soptlist[j]=(soption[0], soption[1], soption_attrs)
                        soptions.extend(soptlist)
                    optlist[i] = (option[0], option[1], soptions, option_attrs)
                options.extend(optlist)
            a_options.append((arch,options))
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


class SystemGroups(Form):
    template = "bkr.server.templates.system_groups"
    member_widgets = ["id", "group", "delete_link"]
    params = ['options', 'readonly', 'group_assocs']
    delete_link = DeleteLinkWidgetForm()

    def __init__(self, *args, **kw):
        super(SystemGroups, self).__init__(*args, **kw)
        self.id    = HiddenField(name="id")
        self.group = AutoCompleteField(name='group',
                                      search_controller=url("/groups/by_name"),
                                      search_param="input",
                                      result_name="matches")

    def update_params(self, d):
        super(SystemGroups, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'group_assocs' in d['options']:
            d['group_assocs'] = d['options']['group_assocs']
        if 'system_id' in d['options']:
            d['system_id'] = d['options']['system_id']


class SystemProvision(Form):
    javascript = [LocalJSLink('bkr', '/static/javascript/provision_v2.js')]
    template = "bkr.server.templates.system_provision"
    member_widgets = ["id", "prov_install", "ks_meta", "power",
                      "koptions", "koptions_post", "reboot","schedule_reserve_days"]
    params = ['options', 'lab_controller', 'power_enabled', 'reserved',
              'provisioning_notes', 'provisioning_panel_id',
              'provisioning_button_label']

    MAX_DAYS_PROVISION = 7
    DEFAULT_RESERVE_DAYS = 0.5

    def __init__(self, *args, **kw):
        super(SystemProvision, self).__init__(*args, **kw)
        self.id           = HiddenField(name="id")
        self.power        = HiddenField(name="power")
        self.schedule_reserve_days = SingleSelectField(name='reserve_days',
                                                       label=_('Days to reserve for'),
                                                       options = range(1, self.MAX_DAYS_PROVISION + 1),
                                                       validator=validators.NotEmpty())
        self.prov_install = SingleSelectField(name='prov_install',
                                             label=_(u'Distro'),
                                             options=[],
                                             attrs={'size': 12, 'class': 'input-block-level'},
                                             validator=validators.NotEmpty())
        self.ks_meta       = TextField(name='ks_meta', attrs=dict(size=50),
                                       label=_(u'KickStart MetaData'))
        self.koptions      = TextField(name='koptions', attrs=dict(size=50),
                                       label=_(u'Kernel Options (Install)'))
        self.koptions_post = TextField(name='koptions_post', 
                                       attrs=dict(size=50),
                                       label=_(u'Kernel Options (Post)'))
        self.reboot        = CheckBox(name='reboot',
                                       label=_(u'Reboot System?'),
                                       default=True)

    def update_params(self, d): 
        super(SystemProvision, self).update_params(d)
        for param in ['reserved', 'lab_controller', 'provisioning_notes',
                      'provisioning_panel_id', 'provisioning_button_label']:
            d[param] = d['options'].get(param)
        if 'power' in d['value']:
            if d['value']['power']:
                d['power_enabled'] = True

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

class SystemNotes(Form):
    template = "bkr.server.templates.system_notes"
    member_widgets = ["id", "note", "delete_link"]
    params = ['options', 'readonly', 'notes']
    delete_link = DeleteLinkWidgetAJAX()

    def __init__(self, *args, **kw):
        super(SystemNotes, self).__init__(*args, **kw)
        self.id = HiddenField(name="id")
        self.note = TextArea(name='note', label=_(u'Note'))

    def update_params(self, d):
        super(SystemNotes, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'notes' in d['options']:
            d['notes'] = d['options']['notes']

class SystemExclude(Form):
    template = """
    <form xmlns:py="http://purl.org/kid/ns#"
          name="${name}"
          action="${action}"
          method="${method}" width="100%">
     ${display_field_for("id")}
     ${display_field_for("excluded_families")}
     <a py:if="not readonly" class="btn btn-primary" href="javascript:document.${name}.submit();">Save Exclude Changes</a>
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

class SystemHistory(CompoundWidget): 
    template = "bkr.server.templates.system_activity"
    member_widgets = ['grid', 'search_bar']
    params = ['searchvalue', 'all_history']
    
    def __init__(self):
        #filter_column_options = model.Activity.distinct_field_names() 
        self.grid  = myPaginateDataGrid(fields = [PaginateDataGrid.Column(name='user',title='User',getter=lambda x: x.user,options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='service', title='Service', getter=lambda x: x.service, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='created', title='Created',
                                                    getter=lambda x: x.created,
                                                    options=dict(sortable=True, datetime=True)),
                                                  PaginateDataGrid.Column(name='field_name', title='Field Name', getter=lambda x: x.field_name, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='action', title='Action', getter=lambda x: x.action, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='old_value',title='Old Value', getter=lambda x: x.old_value,options=dict(sortable=True)), 
                                                  PaginateDataGrid.Column(name='new_value',title='New Value',getter=lambda x: x.new_value, options=dict(sortable=True))]) 

        self.search_bar = SearchBar(name='historysearch',
                           label=_(u'History Search'),    
                           table = search_utility.History.search.create_search_table(),
                           complete_data = search_utility.History.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_history"), 
                           )

    def display(self,value=None,**params):
        if 'options' in params:
            if 'searchvalue' in params['options']:
                params['searchvalue'] = params['options']['searchvalue']
        if 'action' in params:
            params['all_history'] = params['action']
        return super(SystemHistory, self).display(value,**params)
                
    

class SystemForm(Form):
    javascript = [LocalJSLink('bkr', '/static/javascript/provision_v2.js'),
                  LocalJSLink('bkr', '/static/javascript/install_options.js'),
                  LocalJSLink('bkr', '/static/javascript/searchbar_v9.js'),
                  JSLink(static,'ajax.js'),
                 ]
    template = "bkr.server.templates.system_form"
    params = ['id','readonly',
              'user_change','user_change_text', 'running_job',
              'show_loan_options']
    user_change = '/user_change'
    fields = [
               HiddenField(name='id'),
               TextField(name='fqdn',
                         label=_(u'System Name'),
                         validator=Hostname(not_empty=True),
                         attrs={'maxlength':'255',
                                'size':'60'}),
               SingleSelectField(name='status',
                                 label=_(u'Condition'),
                                 options=[(status, unicode(status)) for status in model.SystemStatus],
                                 validator=ValidEnumValue(model.SystemStatus)),
               TextArea(name='status_reason', label=_(u'Condition Report'),attrs={'rows':3,'cols':27},validator=validators.MaxLength(255)),
               SingleSelectField(name='lab_controller_id',
                                 label=_(u'Lab Controller'),
                                 options=lambda: [(0,"None")] + model.LabController.get_all(valid=True),
                                 validator=validators.Int()),
               TextField(name='vendor', label=_(u'Vendor')),
               TextField(name='model', label=_(u'Model')),
               TextField(name='date_added', label=_(u'Date Created')),
               TextField(name='date_modified', label=_(u'Last Modification')),
               TextField(name='date_lastcheckin', label=_(u'Last Inventoried')),
               TextField(name='serial', label=_(u'Serial Number')),
               SingleSelectField(name='type',
                                 label=_(u'Type'),
                                 options=[(type, unicode(type)) for type in model.SystemType],
                                 validator=ValidEnumValue(model.SystemType)),
               TextField(name='location', label=_(u'Location')),
               TextField(name='lender', label=_(u'Lender'),
                         help_text=_(u'Name of the organisation which has '
                            'lent this system to Beaker\'s inventory')),
               TextField(name='user', label=_(u'Current User')),
               TextField(name='owner', label=_(u'Owner')),
               TextField(name='loaned', label=_(u'Loaned To')),
               TextField(name='contact', label=_(u'Contact')),
               AutoCompleteField(name='group',
                                      search_controller=url("/groups/by_name"),
                                      search_param="name",
                                      result_name="groups"),
               TextField(name='mac_address', label=_(u'Mac Address'),
                         attrs={'maxlength': 18}, validator=validators.MaxLength(18)),
               TextField(name='cc', label=_(u'Notify CC')),
               SingleSelectField(name='hypervisor_id',
                                 label=_(u'Hypervisor'),
                                 options=lambda: [(0, 'None')] + model.Hypervisor.get_all_types(),
                                 validator=validators.Int()),
               SingleSelectField(name='kernel_type_id',
                                 label=_(u'Kernel Type'),
                                 options=model.KernelType.get_all_types,
                                 validator=validators.Int()),
    ]

    def display_value(self, item, hidden_fields, value=None):
        if item not in [hfield.name for hfield in hidden_fields]:
            return value

    def display(self, value, options={}, **params):
        # Some loan related options, if we have a value.
        if value:
            params['loan_comment'] = value.loan_comment
            # It's currently loaned or we have perm to add a new loan
            if identity.current.user:
                params['show_loan_options'] = \
                    value.can_return_loan(identity.current.user) or \
                    value.can_lend(identity.current.user) or \
                    value.can_borrow(identity.current.user)
            else:
                params['show_loan_options'] = False
        else:
            params['loan_comment'] = None
            params['show_loan_options'] = None
        if not options.get('edit'):
            params['display_system_property'] = \
                lambda f: self.custom_value_for(f, value)
        return super(SystemForm, self).display(value, options=options, **params)

    def custom_value_for(self, item, value):
        """ Return system property fit for display

        Default is to return the item attribute of value, otherwise
        custom attribute values can be returned.
        """
        mapper = dict(lab_controller_id=lambda: value.lab_controller and \
                                                 value.lab_controller.fqdn,
                      kernel_type_id=lambda: value.kernel_type and \
                                             value.kernel_type.kernel_type,
                      hypervisor_id=lambda: value.hypervisor and \
                                              value.hypervisor.hypervisor)
        property_func = mapper.get(item)
        if property_func:
            property_value = property_func()
        else:
            property_value = getattr(value, item, None)

        span = Element('span', {'class': 'form-control-static'})
        if property_value is not None:
            span.text = unicode(property_value)
        return span

    def update_params(self, d):
        super(SystemForm, self).update_params(d)
        if d['options'].get('edit'):
            d['display_system_property'] = lambda f: self.display_field_for(f, d["value_for"](f))
        if d["options"].has_key("loan"):
            d["loan"] = d["options"]["loan"]
        if d["options"].has_key("report_problem"):
            d["report_problem"] = d["options"]["report_problem"]
        if d["options"].has_key("system_actions"):
            d["system_actions"] = d["options"]["system_actions"]
        else:
            d['system_actions'] = None
        if d["options"].has_key("system"):
            d["system"] = d["options"]["system"]
        if d["options"].has_key("user_change"):
            d["user_change"] = d["options"]["user_change"]
        if d["options"].has_key("user_change_text"):
            d["user_change_text"] = d["options"]["user_change_text"]
        if d["options"].has_key("running_job"):
            d["running_job"] = d["options"]["running_job"]
        d["id"] = d["value_for"]("id")
        if d["value"] and "owner" in d["value"] and d["value"]["owner"]:
            d["owner_email_link"] = d["value"]["owner"].email_link
        else:
            d["owner_email_link"] = ""
        if d["value"] and "user" in d["value"] and d["value"]["user"]:
            d["user_email_link"] = d["value"]["user"].email_link
        else:
            d["user_email_link"] = ""
        if d["value"] and "loaned" in d["value"] and d["value"]["loaned"]:
            d["loaned_email_link"] = d["value"]["loaned"].email_link
        else:
            d["loaned_email_link"] = ""


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
    params = ['recipeset','show_priority','action','priorities_list','can_ack_nak']
    member_widgets = ['priority_widget','retentiontag_widget','ack_panel_widget', 'product_widget', 'action_widget']
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
        if recipeset.can_set_response(user):
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
            d['options']['name'], jsonify.encode(self.get_options(d)), d['action'])})


class RecipeActionWidget(CompoundWidget):
    template = 'bkr.server.templates.recipe_action'
    javascript = [LocalJSLink('bkr', '/static/javascript/util.js'),
        LocalJSLink('bkr', '/static/javascript/jquery-ui-1.9.2.min.js', order=3),]
    css =  [LocalCSSLink('bkr', '/static/css/smoothness/jquery-ui.css')]
    problem_form = ReportProblemForm()
    report_problem_options = {}
    params = ['report_problem_options']
    member_widgets = ['problem_form']

    def __init__(self, *args, **kw):
        super(RecipeActionWidget, self).__init__(*args, **kw)

    def display(self, task, **params):
        if getattr(task.resource, 'system', None):
            params['report_problem_options'] = {'system' : task.resource.system,
                'recipe' : task, 'name' : 'report_problem_recipe_%s' % task.id,
                'action' : '../system_action/report_system_problem'}
        return super(RecipeActionWidget,self).display(task, **params)


class RecipeWidget(CompoundWidget):
    css = []
    template = "bkr.server.templates.recipe_widget"
    params = ['recipe', 'recipe_systems']
    member_widgets = ['action_widget']
    action_widget = RecipeActionWidget()

    def update_params(self, d):
        super(RecipeWidget, self).update_params(d)
        d['recipe_systems'] = \
            make_link(url('../recipes/systems?recipe_id=%d' % d['recipe'].id),
            d['recipe'].dyn_systems.count())

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
        d['attrs']['onchange'] = "ProductChange('%s',%s, %s)" % (
            url(d.get('action')),
            jsonify.encode({'id': d.get('job_id')}),
            jsonify.encode(self.get_options(d)),
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
            jsonify.encode({'id': d.get('job_id')}),
            jsonify.encode(self.get_options(d)),
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


class RequestLoan(RemoteForm):
    template = 'bkr.server.templates.request_loan'
    fields = [TextArea(name='message', label='Loan Request',
        validator=validators.NotEmpty()),]
    member_widgets=['submit']
    desc = 'Request Loan'
    submit = Button(name='submit')
    submit_text = 'Request'
    on_success = 'success(\'Your loan request has been sent succesfully\')'
    on_failure = 'failure(\'We were unable to send you loan request at this time\')';

    def update_params(self, d):
        super(RequestLoan, self).update_params(d)
        d['system'] = d['options']['system']
        d['hidden_fields'] = [HiddenField(name='system', attrs = {'value' : d['system']})]
        d['submit'].attrs.update({'onClick' : "return ! system_action_remote_form_request('%s', %s, '%s');" % (
            d['options']['name'], jsonify.encode(self.get_options(d)), d['action'])})


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
            jsonify.encode(self.get_options(d)))


class SystemActions(CompoundWidget):
    template = 'bkr.server.templates.system_actions'
    problem  = ReportProblemForm(name='problem')
    loan = RequestLoan(name='loan')
    member_widgets = ['problem', 'loan']
    params = ['report_problem_options', 'loan_options']
    name = 'system_actions'


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
            jsonify.encode({'t_id': d['task_details'].get('t_id')}),
            jsonify.encode(self.get_options(d)),
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
