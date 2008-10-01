from turbogears import validators, url, config
import turbogears as tg
from turbojson import jsonify
from turbogears.widgets.rpc import RPC
import model
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea,
                                AutoCompleteField, SingleSelectField, CheckBox,
                                HiddenField, RemoteForm, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, RepeatingFormField,
                                CompoundWidget, AjaxGrid)


class LocalJSLink(JSLink):
    """
    Link to local Javascript files
    """
    def update_params(self, d):
        super(JSLink, self).update_params(d)
        d["link"] = url(self.name)

class Power(CompoundFormField):
    """Dynmaically modifies power arguments based on Power Type Selection"""

    javascript = [LocalJSLink('medusa', '/static/javascript/power.js')]
    template = """
    <div xmlns:py="http://purl.org/kid/ns#" id="${field_id}">
    <script language="JavaScript" type="text/JavaScript">
        PowerManager${field_id} = new PowerManager(
        '${field_id}', '${key_field.field_id}', 
        '${powercontroller_field.field_id}',  
        '${search_controller}', '${system_id}');
        addLoadEvent(PowerManager${field_id}.initialize);
    </script>

    ${key_field.display(value_for(key_field), **params_for(key_field))}
     <table class="powerControlArgs">
      <tr>
       <td><label class="fieldlabel"
                  for="${powercontroller_field.field_id}"
                  py:content="powercontroller_field.label"/>
       </td>
       <td>
        <font color="red">
         <span py:if="error_for(powercontroller_field)"
               class="fielderror"
               py:content="error_for(powercontroller_field)" />
        </font>
        ${powercontroller_field.display(value_for(powercontroller_field), **params_for(powercontroller_field))}
        <span py:if="powercontroller_field.help_text"
              class="fieldhelp"
              py:content="powercontroller_field.help_text" />
       </td>
      </tr>
      <tr>
       <td colspan="2">
        <div class="powerControlArgs" id="powerControlArgs${field_id}"/>
       </td>
      </tr>
     </table>
    </div>
    """
    member_widgets = ["powercontroller_field", "key_field"]
    params = ['search_controller', 'system_id']
    params_doc = {'powertypes_callback' : ''}

    def __init__(self, callback, search_controller, *args, **kw):
        super(Power,self).__init__(*args, **kw)

        self.search_controller=search_controller
        self.powercontroller_field = SingleSelectField(name="powercontroller", options=callback)
	self.key_field = HiddenField(name="key")

class PowerController(CompoundFormField):
    """Dynmaically modifies power arguments based on Power Type Selection"""

    javascript = [LocalJSLink('medusa', '/static/javascript/power.js')]
    template = """
    <div xmlns:py="http://purl.org/kid/ns#" id="${field_id}">
    <script language="JavaScript" type="text/JavaScript">
        PowerControllerManager${field_id} = new PowerControllerManager(
        '${field_id}', '${key_field.field_id}', '${hidden_field.field_id}', 
        '${search_controller}', '${powertype_field.field_id}');
        addLoadEvent(PowerControllerManager${field_id}.initialize);
    </script>

    ${key_field.display(value_for(key_field), **params_for(key_field))}
    ${hidden_field.display(value_for(hidden_field), **params_for(hidden_field))}
     <table class="powerControlArgs">
      <tr>
       <td><label class="fieldlabel"
                  for="${name_field.field_id}"
                  py:content="name_field.label"/>
       </td>
       <td>
        <font color="red">
         <span py:if="error_for(name_field)"
               class="fielderror"
               py:content="error_for(name_field)" />
        </font>
        ${name_field.display(value_for(name_field), **params_for(name_field))}
        <span py:if="name_field.help_text"
              class="fieldhelp"
              py:content="name_field.help_text" />
       </td>
      </tr>
      <tr>
       <td><label class="fieldlabel"
                  for="${powertype_field.field_id}"
                  py:content="powertype_field.label"/>
       </td>
       <td>
        <font color="red">
         <span py:if="error_for(powertype_field)"
               class="fielderror"
               py:content="error_for(powertype_field)" />
        </font>
        ${powertype_field.display(value_for(powertype_field), **params_for(powertype_field))}
        <span py:if="powertype_field.help_text"
              class="fieldhelp"
              py:content="powertype_field.help_text" />
       </td>
      </tr>
      <tr>
       <td colspan="2">
        <div class="powerControlArgs" id="powerControlArgs${field_id}"/>
       </td>
      </tr>
     </table>
    </div>
    """
    member_widgets = ["hidden_field", "name_field", "powertype_field", "key_field"]
    params = ['search_controller']
    params_doc = {'search_controller' : ''}

    def __init__(self, callback, search_controller, *args, **kw):
        super(PowerController,self).__init__(*args, **kw)

        self.search_controller=search_controller
        self.hidden_field = HiddenField(name="id")
        self.key_field = HiddenField(name="key")
        self.name_field = TextField(name="name")
        self.powertype_field = SingleSelectField(name="powertype", options=callback, validator=validators.Int())

class myPaginateDataGrid(PaginateDataGrid):
    template = "medusa.templates.my_paginate_datagrid"

class SearchBar(RepeatingFormField):
    """Search Bar"""

    javascript = [LocalJSLink('medusa', '/static/javascript/searchbar.js')]
    template = """
    <form xmlns:py="http://purl.org/kid/ns#"
      name="${name}"
      action="${action}"
      method="${method}"
      class="searchbar_form"
      py:attrs="form_attrs"
    >
     <table id="${field_id}">
      <thead>
       <tr>
        <th py:for="field in fields">
         <span class="fieldlabel" py:content="field.label" />
        </th>
       </tr>
      </thead> 
      <tbody>
       <tr py:for="repetition in repetitions"
           class="${field_class}"
           id="${field_id}_${repetition}">
        <script language="JavaScript" type="text/JavaScript">
            ${field_id}_${repetition} = new SearchBar(
            '${fields[0].field_id}', '${fields[1].field_id}',
            '${search_controller}', '${value_for(fields[1])}');
            addLoadEvent(${field_id}_${repetition}.initialize);
        </script>
        <td py:for="field in fields">
                <span py:content="field.display(value_for(field),
                      **params_for(field))" />
                <span py:if="error_for(field)" class="fielderror"
                      py:content="error_for(field)" />
                <span py:if="field.help_text" class="fieldhelp"
                      py:content="field_help_text" />
        </td>
        <td>
           <a 
           href="javascript:SearchBarForm.removeItem('${field_id}_${repetition}')">Remove (-)</a>
        </td>
       </tr>
      </tbody>
     </table>
     <a id="doclink" href="javascript:SearchBarForm.addItem('${field_id}');">Add ( + )</a>
     <input type="submit" name="Search" value="Search"/>
    </form>
    """

    params = ['repetitions', 'form_attrs', 'search_controller']
    form_attrs = {}

    def __init__(self, table_callback, search_controller, *args, **kw):
        super(SearchBar,self).__init__(*args, **kw)
        self.search_controller=search_controller
        self.repetitions = 1
        table_field = SingleSelectField(name="table", options=table_callback, validator=validators.NotEmpty())
        column_field = SingleSelectField(name="column", options=[None], validator=validators.NotEmpty())
        operation_field = SingleSelectField(name="operation", options=['equal','like','less than', 'greater than','not equal'], validator=validators.NotEmpty())
        value_field = TextField(name="value")
        self.fields = [ table_field, column_field, operation_field, value_field]

    def display(self, value=None, **params):
        if value and isinstance(value, list) and len(value) > 1:
            params['repetitions'] = len(value)
        #params['repetitions'] = 3
        return super(SearchBar, self).display(value, **params)

class SystemGroups(CompoundWidget):
    template = """
    <div xmlns:py="http://purl.org/kid/ns#">
     <script language="JavaScript" type="text/JavaScript">
      system_group = new SystemGroupManager(
      '${ajaxgrid.id}_AjaxGrid.refresh', '${systemid}', '${removecontroller}');
     </script>
     <span py:replace="ajaxgrid.display()"/>
     <span py:if="not readonly"
           py:replace="remoteform.display(
                value=value,
                on_complete='javascript:%s_AjaxGrid.refresh({&quot;system_id&quot;:%s});' % (ajaxgrid.id, systemid)
       )"/>
    </div>
    """
    params = ['systemid','readonly','ajax_grid_url',
              'search_param','result_name', 'removecontroller']
    systemid = None
    removecontroller = None
    readonly = False
    member_widgets = ["ajaxgrid","remoteform"]
    javascript = [LocalJSLink('medusa', '/static/javascript/systemgroups.js')]

    def __init__(self, ajax_grid_url, search_controller, search_param,
                 result_name, systemid, readonly, removecontroller, *args, **kw):
        self.systemid = systemid
        self.readonly = readonly
        self.removecontroller = removecontroller
        super(SystemGroups,self).__init__(*args, **kw)
        self.ajaxgrid = AjaxGrid(
                  refresh_url = ajax_grid_url,
                  refresh_text = None,
                  defaults = dict(system_id = systemid)
        )
        self.remoteform = RemoteForm(
                             fields = [HiddenField(name='id'),
                                       AutoCompleteField(name='group',
                                         search_controller=search_controller,
                                         search_param=search_param,
                                         result_name=result_name),
                                      ],
                             name   = "remote_form",
                             update = "post_data",
                             action = "/group_add",
                             submit_text = "Add"
        )

class SystemForm(Form):
    template = "medusa.templates.system_form"
    params = ['id','readonly',
              'user_change','user_change_text',
              'owner_change', 'owner_change_text']
    user_change = '/user_change'
    owner_change = '/owner_change'
    fields = [
               HiddenField(name='id'),
               TextField(name='fqdn', 
                         label=_(u'FQDN'), 
                         validator=validators.NotEmpty(),
                         attrs={'maxlength':'255',
                                'size':'100'}),
               SingleSelectField(name='status_id',
                                 label=_(u'Status'),
                                 options=model.SystemStatus.get_all_status),
               TextField(name='vendor', label=_(u'Vendor')),
               TextField(name='model', label=_(u'Model')),
               TextField(name='date_added', label=_(u'Date Added')),
               TextField(name='date_modified', label=_(u'Date Modified')),
               TextField(name='date_lastcheckin', label=_(u'Last Checkin')),
               TextField(name='serial', label=_(u'Serial Number')),
               SingleSelectField(name='type_id',
                                 label=_(u'Type'),
                                 options=model.SystemType.get_all_types),
               TextField(name='location', label=_(u'Location')),
               TextField(name='lender', label=_(u'Lender')),
               TextField(name='user', label=_(u'User')),
               TextField(name='owner', label=_(u'Owner')),
               TextField(name='contact', label=_(u'Contact')),
               CheckBox(name='shared', label=_(u'Shared')),
               CheckBox(name='private', label=_(u'Private')),
               SubmitButton(name='submit', label=_(u'Save Changes')),
    ]

    def display_value(self, item, hidden_fields, value=None):
        if item not in [hfield.name for hfield in hidden_fields]:
            return value

    def update_params(self, d):
        super(SystemForm, self).update_params(d)
        if d["options"].has_key("owner_change"):
            d["owner_change"] = d["options"]["owner_change"]
        if d["options"].has_key("user_change"):
            d["user_change"] = d["options"]["user_change"]
        if d["options"].has_key("owner_change_text"):
            d["owner_change_text"] = d["options"]["owner_change_text"]
        if d["options"].has_key("user_change_text"):
            d["user_change_text"] = d["options"]["user_change_text"]
        d["id"] = d["value_for"]("id")
        if d["options"]["readonly"]:
            d["readonly"] = True
            attrs = {'attrs':{'readonly':'True'}}
            d["display_field_for"] = lambda f: self.display_field_for(f,
                                                                  d["value_for"](f),
                                                                   **attrs)
