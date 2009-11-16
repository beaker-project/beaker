from turbogears import validators, url, config
import turbogears as tg
from turbojson import jsonify
from turbogears.widgets.rpc import RPC
import model
from decimal import Decimal
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea,
                                AutoCompleteField, SingleSelectField, CheckBox,
                                HiddenField, RemoteForm, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, RepeatingFormField,
                                CompoundWidget, AjaxGrid, Tabber, 
                                RepeatingFieldSet, SelectionField)

import logging
log = logging.getLogger('beaker.server')

class UtilJSON:
     @classmethod
     def dynamic_json(cls):
         return lambda param: cls.__return_array_of_json(param)

     @classmethod
     def __return_array_of_json(cls,x):
         if x:
             jsonified_fields = [jsonify.encode(elem) for elem in x]
             return ','.join(jsonified_fields) 
                   

class LocalJSLink(JSLink):
    """
    Link to local Javascript files
    """
    def update_params(self, d):
        super(JSLink, self).update_params(d)
        d["link"] = url(self.name)

class PowerTypeForm(CompoundFormField):
    """Dynmaically modifies power arguments based on Power Type Selection"""

    javascript = [LocalJSLink('beaker', '/static/javascript/power.js')]
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
        super(PowerTypeForm,self).__init__(*args, **kw)

        self.search_controller=search_controller
        self.powercontroller_field = SingleSelectField(name="powercontroller", options=callback)
	self.key_field = HiddenField(name="key")

class myPaginateDataGrid(PaginateDataGrid):
    template = "beaker.server.templates.my_paginate_datagrid"

class SingleSelectFieldJSON(SingleSelectField):
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

class SearchBar(RepeatingFormField):
    """Search Bar"""

    javascript = [LocalJSLink('beaker', '/static/javascript/searchbar_v2.js')]
    template = """
    <div xmlns:py="http://purl.org/kid/ns#">
    <a id="advancedsearch" href="#">Toggle Search</a>
    <form
      id="simpleform"
      name="${name}_simple"
      action="${action}"
      method="${method}"
      class="searchbar_form"
      py:attrs="form_attrs"
      style="display:${simple}"
    >
    <table>
     <tr>
      <td><input type="text" name="simplesearch" value="${simplesearch}" class="textfield"/>
      </td>
      <td><input type="submit" name="search" value="Search"/>
      </td>
     </tr>
    </table>
    </form>
    <form 
      id="searchform"
      name="${name}"
      action="${action}"
      method="${method}"
      class="searchbar_form"
      py:attrs="form_attrs"
      style="display:${advanced}"
    >
    <fieldset>
     <legend>Search</legend>
     <table>
     <tr>
     <td>
     <table id="${field_id}">
      <thead>
       <tr> 
        <th  py:for="field in fields"> 
         <span class="fieldlabel" py:content="field.label" />
        </th>
       </tr>
      </thead> 
      <tbody>
       <tr py:for="repetition in repetitions"
           class="${field_class}"
           id="${field_id}_${repetition}">
        <script language="JavaScript" type="text/JavaScript">
             
            ${field_id}_${repetition} = new SearchBar([${to_json(fields)}],'${search_controller}','${value_for(this_operations_field)}',${extra_callbacks_stringified},${table_search_controllers_stringified});
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
     </td><td>
     <input type="submit" name="Search" value="Search"/>
     </td>
     </tr>
     <tr>
     <td colspan="2">
     <a id="doclink" href="javascript:SearchBarForm.addItem('${field_id}');">Add ( + )</a>
     </td>
     </tr>
     </table>
     </fieldset>
    </form>
    <script type="text/javascript">
    $(document).ready(function() {
        $('#advancedsearch').click( function() { $('#searchform').toggle('slow');
                                                 $('#simpleform').toggle('slow');});
    });
    </script>
    </div>
    """

    params = ['repetitions', 'form_attrs', 'search_controller', 'simplesearch',
              'advanced', 'simple','to_json','this_operations_field','extra_callbacks_stringified','table_search_controllers_stringified']
    form_attrs = {}
    simplesearch = None

    def __init__(self, table,search_controller,extra_selects = None,extra_inputs = None, *args, **kw):
        super(SearchBar,self).__init__(*args, **kw)
        self.search_controller=search_controller
        self.repetitions = 1 
      
        table_field = SingleSelectFieldJSON(name="table", options=table, validator=validators.NotEmpty()) 
        operation_field = SingleSelectFieldJSON(name="operation", options=[None], validator=validators.NotEmpty())
        value_field = TextFieldJSON(name="value")
        
        # We don't know where in the fields array the operation array will be, so we will put it here
        # to access in the template
        self.this_operations_field = operation_field
        self.fields = [table_field,operation_field,value_field] 
       
        new_selects = []
        self.extra_callbacks = {}
        if extra_selects is not None: 
            new_class = [] 
            for elem in extra_selects:
                if elem.has_key('display'):
                    if elem['display'] == 'none':
                        new_class.append('hide_parent') 
                callback = elem.get('callback',None)
                if callback:
                    self.extra_callbacks[elem['name']] = callback    
                new_select = SingleSelectFieldJSON(name=elem['name'],options=callback, css_classes = new_class, validator=validators.NotEmpty(),for_column=elem['column'] )
               
                if elem.has_key('pos'):
                    self.fields.insert(elem['pos'] - 1,new_select)
                else:
                    self.fields.append(new_select) 

        new_inputs = []
        if extra_inputs is not None:
            for the_name in extra_inputs:
                new_input = TextField(name=the_name,display='none')
                new_inputs.append(new_input)   

        controllers = kw.get('table_search_controllers','') 
        self.table_search_controllers_stringified = str(controllers)
        self.to_json = UtilJSON.dynamic_json() 
        self.extra_callbacks_stringified = str(self.extra_callbacks)
        self.fields.extend(new_inputs)
        self.fields.extend(new_selects)
 

    def display(self, value=None, **params):
        if 'options' in params and 'simplesearch' in params['options']:
            params['simplesearch'] = params['options']['simplesearch']
        if value and not params['simplesearch']:
            params['advanced'] = 'True'
            params['simple'] = 'none'
        else:
            params['advanced'] = 'none'
            params['simple'] = 'True'
        if value and isinstance(value, list) and len(value) > 1:
            params['repetitions'] = len(value)
        return super(SearchBar, self).display(value, **params)

class ProvisionForm(RepeatingFormField):
    pass

class PowerActionForm(Form):
    template = "beaker.server.templates.system_power_action"
    member_widgets = ["id", "power", "lab_controller"]
    params = ['options', 'action', 'enabled']
    
    def __init__(self, *args, **kw):
        super(PowerActionForm, self).__init__(*args, **kw)
	self.id = HiddenField(name="id")
        self.power = HiddenField(name="power")
        self.lab_controller = HiddenField(name="lab_controller")

    def update_params(self, d):
        super(PowerActionForm, self).update_params(d)
        if 'power' in d['value'] and 'lab_controller' in d['value']:
            if d['value']['power']:
                d['enabled'] = True

class LabInfoForm(Form):
    template = "beaker.server.templates.system_labinfo"
    member_widgets = ["id", "labinfo", "orig_cost", "curr_cost", "dimensions",
                      "weight", "wattage", "cooling"]
    params = ['options']

    def __init__(self, *args, **kw):
        super(LabInfoForm, self).__init__(*args, **kw)
	self.id = HiddenField(name="id")
        self.labinfo = HiddenField(name="labinfo")
        self.orig_cost = TextField(name='orig_cost', label=_(u'Original Cost'),
                                   validator=validators.Money())
        self.curr_cost = TextField(name='curr_cost', label=_(u'Current Cost'),
                                   validator=validators.Money())
        self.dimensions = TextField(name='dimensions', label=_(u'Dimensions'))
        self.weight = TextField(name='weight', label=_(u'Weight'),
                                   validator=validators.Int())
        self.wattage = TextField(name='wattage', label=_(u'Wattage'),
                                   validator=validators.Int())
        self.cooling = TextField(name='cooling', label=_(u'Cooling'),
                                   validator=validators.Int())

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

class PowerForm(Form):
    template = "beaker.server.templates.system_power"
    member_widgets = ["id", "power", "power_type_id", "power_address", 
                      "power_user", "power_passwd", "power_id"]
    params = []
    params_doc = {}

    def __init__(self, *args, **kw):
        super(PowerForm, self).__init__(*args, **kw)
	self.id = HiddenField(name="id")
        self.power = HiddenField(name="power")
        self.power_type_id = SingleSelectField(name='power_type_id',
                                           label=_(u'Power Type'),
                                           options=model.PowerType.get_all)
        self.power_address = TextField(name='power_address', label=_(u'Power Address'))
        self.power_user = TextField(name='power_user', label=_(u'Power Login'))
        self.power_passwd = TextField(name='power_passwd', label=_(u'Power Password'))
        self.power_id = TextField(name='power_id', label=_(u'Power Port/Plug/etc'))

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


class ExcludedFamilies(FormField):
    template = """
    <ul xmlns:py="http://purl.org/kid/ns#"
        class="${field_class}"
        id="${field_id}"
        py:attrs="list_attrs"
    >
     <li py:for="arch, a_options in options">
      <label for="${field_id}_${arch}" py:content="arch" />
      <ul xmlns:py="http://purl.org/kid/ns#"
          class="${field_class}"
          id="${field_id}_${arch}"
          py:attrs="list_attrs"
      >
       <li py:for="value, desc, subsection, attrs in a_options">
        <input type="checkbox"
               name="${name}.${arch}"
               id="${field_id}_${value}"
               value="${value}"
               py:attrs="attrs"
        />
        <label for="${field_id}_${value}" py:content="desc" />
        <ul xmlns:py="http://purl.org/kid/ns#"
            class="${field_class}"
            id="${field_id}_${value}_sub"
            py:attrs="list_attrs"
        >
         <li py:for="subvalue, subdesc, attrs  in subsection">
          <input type="checkbox"
                 name="${name}_subsection.${arch}"
                 id="${field_id}_${value}_sub_${subvalue}"
                 value="${subvalue}"
                 py:attrs="attrs"
          />
          <label for="${field_id}_${value}_sub_${subvalue}" py:content="subdesc" />
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
    template = "beaker.server.templates.system_keys"
    member_widgets = ["id", "key_name", "key_value"]
    params = ['options', 'readonly', 'key_values_int', 'key_values_string']

    def __init__(self, *args, **kw):
        super(SystemKeys, self).__init__(*args, **kw)
	self.id = HiddenField(name="id")
        self.key_name = TextField(name='key_name', label=_(u'Key'))
        self.key_value = TextField(name='key_value', label=_(u'Value'))

    def update_params(self, d):
        super(SystemKeys, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'key_values_int' in d['options']:
            d['key_values_int'] = d['options']['key_values_int']
        if 'key_values_string' in d['options']:
            d['key_values_string'] = d['options']['key_values_string']

class SystemArches(Form):
    template = "beaker.server.templates.system_arches"
    member_widgets = ["id", "arch"]
    params = ['options', 'readonly', 'arches']

    def __init__(self, *args, **kw):
        super(SystemArches, self).__init__(*args, **kw)
	self.id    = HiddenField(name="id")
        self.arch  = AutoCompleteField(name='arch',
                                      search_controller=url("/arches/by_name"),
                                      search_param="name",
                                      result_name="arches")

    def update_params(self, d):
        super(SystemArches, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'arches' in d['options']:
            d['arches'] = d['options']['arches']
        
class DistroTags(Form):
    template = "beaker.server.templates.distro_tags"
    member_widgets = ["id", "tag"]
    params = ['options', 'readonly', 'tags']

    def __init__(self, *args, **kw):
        super(DistroTags, self).__init__(*args, **kw)
	self.id    = HiddenField(name="id")
        self.tag = AutoCompleteField(name='tag',
                                      search_controller=url("/tags/by_tag"),
                                      search_param="tag",
                                      result_name="tags")

    def update_params(self, d):
        super(DistroTags, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'tags' in d['options']:
            d['tags'] = d['options']['tags']

class SystemGroups(Form):
    template = "beaker.server.templates.system_groups"
    member_widgets = ["id", "group"]
    params = ['options', 'readonly', 'groups']
    
    def __init__(self, *args, **kw):
        super(SystemGroups, self).__init__(*args, **kw)
	self.id    = HiddenField(name="id")
        self.group = AutoCompleteField(name='group',
                                      search_controller=url("/groups/by_name"),
                                      search_param="name",
                                      result_name="groups")

    def update_params(self, d):
        super(SystemGroups, self).update_params(d)
        if 'readonly' in d['options']:
            d['readonly'] = d['options']['readonly']
        if 'groups' in d['options']:
            d['groups'] = d['options']['groups']

class SystemProvision(Form):
    javascript = [LocalJSLink('beaker', '/static/javascript/provision.js')]
    template = "beaker.server.templates.system_provision"
    member_widgets = ["id", "prov_install", "ks_meta", "power",
                      "koptions", "koptions_post", "reboot"]
    params = ['options', 'is_user', 'lab_controller', 'power_enabled']
    
    def __init__(self, *args, **kw):
        super(SystemProvision, self).__init__(*args, **kw)
	self.id           = HiddenField(name="id")
	self.power        = HiddenField(name="power")
        self.prov_install = SingleSelectField(name='prov_install',
                                             label=_(u'Distro'),
                                             options=[],
                                             attrs=dict(size=10),
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
        if 'is_user' in d['options']:
            d['is_user'] = d['options']['is_user']
        if 'lab_controller' in d['options']:
            d['lab_controller'] = d['options']['lab_controller']
        if 'power' in d['value']:
            if d['value']['power']:
                d['power_enabled'] = True

class SystemInstallOptions(Form):
    template = "beaker.server.templates.system_installoptions"
    member_widgets = ["id", "prov_arch", "prov_osmajor", "prov_osversion",
                       "prov_ksmeta", "prov_koptions", "prov_koptionspost"]
    params = ['options', 'readonly', 'provisions']
    
    def __init__(self, *args, **kw):
        super(SystemInstallOptions, self).__init__(*args, **kw)
	self.id                = HiddenField(name="id")
        self.prov_arch         = SingleSelectField(name='prov_arch',
                                 label=_(u'Arch'),
                                 options=[],
                                 validator=validators.NotEmpty())
        self.prov_osmajor      = SingleSelectField(name='prov_osmajor',
                                 label=_(u'Family'),
                                 options=model.OSMajor.get_all)
        self.prov_osversion    = SingleSelectField(name='prov_osversion',
                                 label=_(u'Update'),
                                 options=model.OSVersion.get_all)
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
    template = "beaker.server.templates.system_notes"
    member_widgets = ["id", "note"]
    params = ['options', 'readonly', 'notes']

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
          action="${tg.url(action)}"
          method="${method}" width="100%">
     ${display_field_for("id")}
     ${display_field_for("excluded_families")}
     <a py:if="not readonly" class="button" href="javascript:document.${name}.submit();">Save Exclude Changes</a>
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
    template = "beaker.server.templates.system_details"
    params = ['system']

class SystemHistory(Widget):
    template = "beaker.server.templates.system_activity"
    params = ['system']

class SystemForm(Form):
    javascript = [LocalJSLink('beaker', '/static/javascript/provision.js')]
    template = "beaker.server.templates.system_form"
    params = ['id','readonly',
              'user_change','user_change_text',
              'loan_change', 'loan_text',
              'owner_change', 'owner_change_text']
    user_change = '/user_change'
    owner_change = '/owner_change'
    loan_change = '/loan_change'
    fields = [
               HiddenField(name='id'),
               TextField(name='fqdn', 
                         label=_(u'FQDN'), 
                         validator=validators.NotEmpty(),
                         attrs={'maxlength':'255',
                                'size':'60'}),
               SingleSelectField(name='status_id',
                                 label=_(u'Status'),
                                 options=model.SystemStatus.get_all_status,
                                 validator=validators.NotEmpty()),
               SingleSelectField(name='lab_controller_id',
                                 label=_(u'Lab Controller'),
                                 options=model.LabController.get_all),
               TextField(name='vendor', label=_(u'Vendor')),
               TextField(name='model', label=_(u'Model')),
               TextField(name='date_added', label=_(u'Date Added')),
               TextField(name='date_modified', label=_(u'Date Modified')),
               TextField(name='date_lastcheckin', label=_(u'Last Checkin')),
               TextField(name='serial', label=_(u'Serial Number')),
               SingleSelectField(name='type_id',
                                 label=_(u'Type'),
                                 options=model.SystemType.get_all_types,
                                 validator=validators.NotEmpty()),
               TextField(name='location', label=_(u'Location')),
               TextField(name='lender', label=_(u'Lender')),
               TextField(name='user', label=_(u'User')),
               TextField(name='owner', label=_(u'Owner')),
               TextField(name='loaned', label=_(u'Loaned To')),
               TextField(name='contact', label=_(u'Contact')),
               CheckBox(name='shared', label=_(u'Shared')),
               CheckBox(name='private', label=_(u'Secret (NDA)')),
               Tabber(use_cookie=True),
               AutoCompleteField(name='group',
                                      search_controller=url("/groups/by_name"),
                                      search_param="name",
                                      result_name="groups"),
               TextField(name='mac_address', label=_(u'Mac Address')),
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
        if d["options"].has_key("loan_change"):
            d["loan_change"] = d["options"]["loan_change"]
        if d["options"].has_key("loan_text"):
            d["loan_text"] = d["options"]["loan_text"]
        d["id"] = d["value_for"]("id")

        if d["options"]["readonly"]:
	    d["readonly"] = True
 	    attrs = {'attrs':{'readonly':'True'}}
 	    d["display_field_for"] = lambda f: self.display_field_for(f,
                                                          d["value_for"](f),
                                                                  **attrs)
