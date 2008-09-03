from turbogears import validators, url, config
import model
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea,
                                AutoCompleteField, SingleSelectField, CheckBox,
                                HiddenField, RemoteForm, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, RepeatingFormField)


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

    params = ['repetitions', 'search_controller']

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
