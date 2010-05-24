from turbogears import validators, url, config
import turbogears as tg
from turbojson import jsonify
from turbogears.widgets.rpc import RPC
from sqlalchemy import distinct
import model
import re
import search_utility
from decimal import Decimal
from turbogears.widgets import (Form, TextField, SubmitButton, TextArea, Label,
                                AutoCompleteField, SingleSelectField, CheckBox,
                                HiddenField, RemoteForm, LinkRemoteFunction, CheckBoxList, JSLink,
                                Widget, TableForm, FormField, CompoundFormField,
                                static, PaginateDataGrid, DataGrid, RepeatingFormField,
                                CompoundWidget, AjaxGrid, Tabber, CSSLink,
                                RadioButtonList, MultipleSelectField, Button,
                                RepeatingFieldSet, SelectionField,WidgetsList)
import logging
log = logging.getLogger(__name__)

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


class LocalCSSLink(CSSLink):
    """
    Link to local CSS files
    """
    def update_params(self, d):
        super(CSSLink, self).update_params(d)
        d["link"] = url(self.name)


class PowerTypeForm(CompoundFormField):
    """Dynmaically modifies power arguments based on Power Type Selection"""
    javascript = [LocalJSLink('bkr', '/static/javascript/power.js')]
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

class ReserveSystem(TableForm):
    fields = [
	      HiddenField(name='distro_id'),
	      HiddenField(name='system_id'),
              Label(name='system', label=_(u'System to Provision')),
              Label(name='distro', label=_(u'Distro to Provision')),
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

class ReserveWorkflow(Form): 
    javascript = [LocalJSLink('bkr', '/static/javascript/reserve_workflow.js')] 
    template="bkr.server.templates.reserve_workflow"
    css = [LocalCSSLink('bkr','/static/css/reserve_workflow.css')] 
    member_widgets = ['arch','distro','distro_family','method_','tag'] 
    params = ['arch_value','method_value','tag_value','distro_family_value','all_arches',
              'all_tags','all_methods','all_distro_familys','to_json','auto_pick'] 

    def __init__(self,*args,**kw):
        super(ReserveWorkflow,self).__init__(*args, **kw)  
        def my_cmp(x,y):
            m1 = re.search('^(.+?)(\d{1,})?$',x)
            m2 = re.search('^(.+?)(\d{1,})?$',y)
            try:
                distro_1 = m1.group(1).lower() 
            except AttributeError,e:
                #x has no value, it goes first
                return -1

            try:
                distro_2 = m2.group(1).lower() 
            except AttributeError,e:
                #y has no value, it goes first 
                return 1

            distro_1_ver = int(m1.group(2) or 0)
            distro_2_ver = int(m2.group(2) or 0)

            if not distro_1 or not distro_2:
                return distro_1 and 1 or -1
            if distro_1 == distro_2: 
                #Basically,if x has no version or is a lower version than y, it goes first 
                return distro_1_ver and (distro_2_ver and (distro_1_ver < distro_2_ver and -1 or 1)  or 1) or -1 
            else:
                #Sort distro alphabetically,diregarding version
                return distro_1 < distro_2 and -1 or 1
                              
        self.all_arches = [['','None Selected']] + [[elem.arch,elem.arch] for elem in model.Arch.query()]
        self.all_tags = [['','None Selected']] + [[elem.tag,elem.tag] for elem in model.DistroTag.query()]  
        self.all_methods = [('','None Selected')] + [[elem,elem] for elem in model.Distro.all_methods()]
        e = [elem.osmajor for elem in model.OSMajor.query()] 
        self.all_distro_familys = [('','None Selected')] + [[osmajor,osmajor] for osmajor in sorted(e,cmp=my_cmp )]  

        self.method_ = SingleSelectField(name='method', label='Method', options=[None],validator=validators.NotEmpty())
        self.distro = SingleSelectField(name='distro', label='Distro', 
                                        options=[('','None available')],validator=validators.NotEmpty())
        self.distro_family = SingleSelectField(name='distro_family', label='Distro Family', 
                                               options=[None],validator=validators.NotEmpty())
        self.tag = SingleSelectField(name='tag', label='Tag', options=[None],validator=validators.NotEmpty())
        self.arch = SingleSelectField(name='arch', label='Arch', options=[None],validator=validators.NotEmpty())

        self.to_json = UtilJSON.dynamic_json()
        self.auto_pick = Button(default="Auto pick system", name='auto_pick', attrs={'class':None})
        self.name = 'reserveworkflow_form'
        self.action = '/reserve_system'
        self.submit = SubmitButton(name='search',attrs={'value':'Show Systems'})
                                                                
    def display(self,value=None,**params):
        if 'options' in params:
            for k in params['options'].keys():
                params[k] = params['options'][k]
                del params['options'][k]
        return super(ReserveWorkflow,self).display(value,**params)

    def update_params(self,d):
        super(ReserveWorkflow,self).update_params(d) 
        if 'values' in d:
            if d['values']:
                d['arch_value'] = d['values']['arch'] 
                d['distro_family_value'] = d['values']['distro_family']
                d['tag_value'] = d['values']['tag']
                d['method_value'] = d['values']['method']

class MyButton(Widget):
    template="bkr.server.templates.my_button"
    params = ['submit','button_label','name']
    def __init__(self,name,submit=True,*args,**kw): 
        self.submit = submit 
        self.name = name
        self.button_label = None

    def display(self,value,**params):
        if 'options' in params:
            if 'label' in params['options']:
                params['button_label'] = params['options']['label']       
            if 'name' in params['options']:
                params['name'] = params['options']['name']
        return super(MyButton,self).display(value,**params)


class myDataGrid(DataGrid):
    template = "bkr.server.templates.my_datagrid"
    name = "my_datagrid"
    
class InnerGrid(DataGrid):
    template = "bkr.server.templates.inner_grid" 
    params = ['show_headers']
    
    def display(self,value=None,**params):
        if 'options' in params:
            if 'show_headers' in params['options']:
                params['show_headers'] = params['options']['show_headers']
        return super(InnerGrid,self).display(value,**params)

class myPaginateDataGrid(PaginateDataGrid):
    template = "bkr.server.templates.my_paginate_datagrid"


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


class JobMatrixReport(Form):     
    javascript = [LocalJSLink('bkr', '/static/javascript/job_matrix.js')]
    css = [LocalCSSLink('bkr','/static/css/job_matrix.css')] 
    template = 'bkr.server.templates.job_matrix' 
    member_widgets = ['whiteboard','job_ids','generate_button'] 
    params = ['list','whiteboard_filter','whiteboard_options','job_ids_vals']
    default_validator = validators.NotEmpty() 
    def __init__(self,*args,**kw): 
        super(JobMatrixReport,self).__init__(*args, **kw)       
        self.class_name = self.__class__.__name__
        if 'whiteboard_options' in kw:
            whiteboard_options = kw['whiteboard_options']
        else:
            whiteboard_options = []

        self.whiteboard_options = whiteboard_options or []
      
        self.whiteboard = SingleSelectField('whiteboard',label='Whiteboard',attrs={'size':5}, options=whiteboard_options, validator=self.default_validator) 
        self.job_ids = TextArea('job_ids',label='Job ID', rows=7,cols=7, validator=self.default_validator) 
        self.whiteboard_filter = TextField('whiteboard_filter', label='Filter Whiteboard') 

        self.name='remote_form' 
        self.action = '.'   
    
    def display(self,**params):     
        if 'options' in params:
            if 'whiteboard_options' in params['options']:
                params['whiteboard_options'] = params['options']['whiteboard_options'] 
            if 'job_ids_vals' in params['options']:
                params['job_ids_vals'] = params['options']['job_ids_vals']
            if 'grid' in params['options']:              
                params['grid'] = params['options']['grid'] 
            if 'list' in params['options']: 
                params['list'] = params['options']['list']
        return super(JobMatrixReport,self).display(value=None,**params)


class SearchBar(RepeatingFormField):
    """Search Bar""" 
    javascript = [LocalJSLink('bkr', '/static/javascript/searchbar_v5.js')]
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
    <span py:for="hidden in extra_hiddens or []">
        <input type='hidden' id='${hidden[0]}' name='${hidden[0]}' value='${hidden[1]}' />
    </span> 
    <table>
     <tr>
      <td><input type="text" name="simplesearch" value="${simplesearch}" class="textfield"/>
      </td>
    <td><input type="submit" name="search" value="${simplesearch_label}"/>

     <span style="margin:0 0.5em 0.5em 0.5em;" py:for="quickly_search in quickly_searches">
        ${button_widget.display(value=quickly_search[1],options=dict(label=quickly_search[0]))}
     </span>
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

    <span py:for="hidden in extra_hiddens or []">
        <input type='hidden' id='${hidden[0]}' name='${hidden[0]}' value='${hidden[1]}' />
    </span> 
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
            
            ${field_id}_${repetition} = new SearchBar([${to_json(fields)}],'${search_controller}','${value_for(this_operations_field)}',${extra_callbacks_stringified},${table_search_controllers_stringified},'${value_for(this_searchvalue_field)}','${value_for(keyvaluevalue)}');
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
     </table></td><td>
     <input type="submit" name="Search" value="Search"/> 
     </td>
   
     </tr>
     <tr>
     <td colspan="2">
     <a id="doclink" href="javascript:SearchBarForm.addItem('${field_id}');">Add ( + )</a>
     </td>
     </tr>
     </table>
    
    <a py:if="enable_custom_columns" id="customcolumns" href="#">Toggle Result Columns</a> 
    <div style='display:none'  id='selectablecolumns'>
      <ul class="${field_class}" id="${field_id}">
        <li py:if="col_options" py:for="value,desc in col_options">
          <input py:if="col_defaults.get(value)" type="checkbox" name = "${field_id}_column_${value}" id="${field_id}_column_${value}" value="${value}" checked='checked' />
          <input py:if="not col_defaults.get(value)" type="checkbox" name = "${field_id}_column_${value}" id="${field_id}_column_${value}" value="${value}" />
          <label for="${field_id}_${value}" py:content="desc" />
        </li>  
      </ul>
    <a style='margin-left:10px' id="selectnone" href="#">Select None</a>
    <a style='margin-left:10px' id="selectall" href="#">Select All</a>
    <a style='margin-left:10px' id="selectdefault" href="#">Select Default</a>
    </div> 
     </fieldset>  
    </form>
    <script type="text/javascript">
    $(document).ready(function() {
        $('#advancedsearch').click( function() { $('#searchform').toggle('slow');
                                                 $('#simpleform').toggle('slow');});
   

  
        $('#customcolumns').click( function() { $('#selectablecolumns').toggle('slow'); });
        
        $('#selectnone').click( function() { $("input[name *= 'systemsearch_column_']").removeAttr('checked'); }); 
        $('#selectall').click( function() { $("input[name *= 'systemsearch_column_']").attr('checked',1); });
        $('#selectdefault').click( function() { $("input[name *= 'systemsearch_column_']").each( function() { select_only_default($(this))}) });

        function select_only_default(obj) {
            var defaults = ${default_result_columns}
            var current_item = obj.val()
            var the_name = 'systemsearch_column_'+current_item
             if (defaults[current_item] == 1) {
                 $("input[name = '"+the_name+"']").attr('checked',1); 
             } else {
                 $("input[name = '"+the_name+"']").removeAttr('checked');  
             }
         }
     });


    </script>
    </div>
    """

    params = ['repetitions', 'form_attrs', 'search_controller', 'simplesearch','quickly_searches','button_widget',
              'advanced', 'simple','to_json','this_operations_field','this_searchvalue_field','extra_hiddens',
              'extra_callbacks_stringified','table_search_controllers_stringified','keyvaluevalue','simplesearch_label',
              'result_columns','col_options','col_defaults','enable_custom_columns','default_result_columns']
    form_attrs = {}
    simplesearch = None

    def __init__(self, table,search_controller,extra_selects=None, extra_inputs=None,extra_hiddens=None, enable_custom_columns=False, *args, **kw): 
        super(SearchBar,self).__init__(*args, **kw)
        self.enable_custom_columns = enable_custom_columns
        self.search_controller=search_controller
        self.repetitions = 1 
        self.extra_hiddens = extra_hiddens
        self.default_result_columns = {}
        table_field = SingleSelectFieldJSON(name="table", options=table, validator=validators.NotEmpty()) 
        operation_field = SingleSelectFieldJSON(name="operation", options=[None], validator=validators.NotEmpty())
        value_field = TextFieldJSON(name="value") 
        # We don't know where in the fields array the operation array will be, so we will put it here
        # to access in the template
        self.this_operations_field = operation_field
        self.this_searchvalue_field = value_field
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

        self.button_widget = MyButton(name='quick_search')
        self.quickly_searches = []
        if 'quick_searches' in kw:
            if kw['quick_searches'] is not None: 
                for elem,name in kw['quick_searches']:
                    vals = elem.split('-')
                    if len(vals) != 3:
                        log.error('Quick searches expects vals as <column>-<operation>-<value>. The following is incorrect: %s' % (elem)) 
                    else: 
                        self.quickly_searches.append((name, '%s-%s-%s' % (vals[0],vals[1],vals[2])))

        controllers = kw.get('table_search_controllers',dict()) 
         
        self.table_search_controllers_stringified = str(controllers)
        self.to_json = UtilJSON.dynamic_json()
        
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
      
     

class ProvisionForm(RepeatingFormField):
    pass

class PowerActionForm(Form):
    template = "bkr.server.templates.system_power_action"
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

class TaskSearchForm(RemoteForm):
    template = "bkr.server.templates.task_search_form"
    member_widgets = ['system_id', 'system', 'task', 'distro', 'family', 'arch', 'start', 'finish', 'status', 'result']
    params = ['options','hidden']
    fields = [HiddenField(name='system_id', validator=validators.Int()),
              HiddenField(name='distro_id', validator=validators.Int()),
              HiddenField(name='task_id', validator=validators.Int()),
              TextField(name='task', label=_(u'Task')),
#              AutoCompleteField(name='task',
#                                search_controller=url('/tasks/by_name'),
#                                search_param='task',
#                                result_name='tasks'),
              TextField(name='system', label=_(u'System')),
              SingleSelectField(name='arch_id', label=_(u'Arch'),validator=validators.Int(),
                                options=model.Arch.get_all),
              TextField(name='distro', label=_(u'Distro')),
              TextField(name='whiteboard', label=_(u'Recipe Whiteboard')),
#              AutoCompleteField(name='distro',
#                                search_controller=url('/distros/by_name'),
#                                search_param='distro',
#                                result_name='distros'),
              SingleSelectField(name='osmajor_id', label=_(u'Family'),validator=validators.Int(),
                                options=model.OSMajor.get_all),
              SingleSelectField(name='status_id', label=_(u'Status'),validator=validators.Int(),
                                options=model.TaskStatus.get_all),
              SingleSelectField(name='result_id', label=_(u'Result'),validator=validators.Int(),
                                options=model.TaskResult.get_all),
             ]

#    def__init__(self, *args, **kw):
#        super(TaskSearchForm, self).__init__(*args, **kw)
#        self.system_id = HiddenField(name='system_id')
#        self.system    = TextField(name='system', label=_(u'System'))
#        self.task      = TextField(name='task', label=_(u'Task'))

    def update_params(self, d):
        print "d=", d
        super(TaskSearchForm, self).update_params(d)
        if 'arch_id' in d['options']:
            d['arch_id'] = d['options']['arch_id']


class LabInfoForm(Form):
    template = "bkr.server.templates.system_labinfo"
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
    template = "bkr.server.templates.system_power"
    member_widgets = ["id", "power", "power_type_id", "power_address", 
                      "power_user", "power_passwd", "power_id",
                       "release_action_id", "reprovision_distro_id"]
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
        self.release_action_id = RadioButtonList(name='release_action_id',
                                             label=_(u'Release Action'),
                                           options=model.ReleaseAction.get_all,
                                            default=1,
                                             validator=validators.NotEmpty())
        self.reprovision_distro_id = SingleSelectField(name='reprovision_distro_id',
                                                label=_(u'Reprovision Distro'),
                                                options=[],
                                             validator=validators.NotEmpty())

    def update_params(self, d):
        super(PowerForm, self).update_params(d)
        if 'release_action' in d['value']:
            release_action = d['value']['release_action']
            d['value']['release_action_id'] = release_action.id
        if 'reprovision_distro' in d['value']:
            reprovision_distro = d['value']['reprovision_distro']
            d['value']['reprovision_distro_id'] = reprovision_distro.id
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
    template = "bkr.server.templates.system_keys"
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
    template = "bkr.server.templates.system_arches"
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
    template = "bkr.server.templates.distro_tags"
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
    template = "bkr.server.templates.system_groups"
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
    javascript = [LocalJSLink('bkr', '/static/javascript/provision.js')]
    template = "bkr.server.templates.system_provision"
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
    template = "bkr.server.templates.system_installoptions"
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
    template = "bkr.server.templates.system_notes"
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
    template = "bkr.server.templates.system_details"
    params = ['system']

class SystemHistory(CompoundWidget): 
    template = "bkr.server.templates.system_activity"
    params = ['list','grid','search_bar','searchvalue','all_history'] 
    
    def __init__(self):
        #filter_column_options = model.Activity.distinct_field_names() 
        self.grid  = myPaginateDataGrid(fields = [PaginateDataGrid.Column(name='user',title='User',getter=lambda x: x.user,options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='service', title='Service', getter=lambda x: x.service, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='created', title='Created', getter=lambda x: x.created, options = dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='field_name', title='Field Name', getter=lambda x: x.field_name, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='action', title='Action', getter=lambda x: x.action, options=dict(sortable=True)),
                                                  PaginateDataGrid.Column(name='old_value',title='Old Value', getter=lambda x: x.old_value,options=dict(sortable=True)), 
                                                  PaginateDataGrid.Column(name='new_value',title='New Value',getter=lambda x: x.new_value, options=dict(sortable=True))]) 

        self.search_bar = SearchBar(name='historysearch',
                           label=_(u'History Search'),    
                           table = search_utility.History.search.create_search_table(),
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
    javascript = [LocalJSLink('bkr', '/static/javascript/provision.js'),
                  LocalJSLink('bkr', '/static/javascript/searchbar_v5.js'),
                  JSLink(static,'ajax.js'),
                 ]
    template = "bkr.server.templates.system_form"
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
               TextArea(name='status_reason', label=_(u'Condition Report'),attrs={'rows':3,'cols':27},validator=validators.MaxLength(255)),
               SingleSelectField(name='lab_controller_id',
                                 label=_(u'Lab Controller'),
                                 options=[(0,"None")] + model.LabController.get_all()),
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

class TasksWidget(CompoundWidget):
    template = "bkr.server.templates.tasks_widget"
    params = ['tasks', 'hidden','action']
    member_widgets = ['link'] 
    action = './do_search'
    link = LinkRemoteFunction(name='link', method='post')

class RecipeTasksWidget(TasksWidget):
    
     
    def update_params(self, d):
        d["hidden"] = dict(system  = 1,
                           arch    = 1,
                           distro  = 1,
                           osmajor = 1,
                          )

class RecipeSetWidget(CompoundWidget):
    javascript = []
    css = []
    template = "bkr.server.templates.recipe_set"
    params = ['recipeset','show_priority']
    member_widgets = ['priority_widget']

    def __init__(self,*args,**kw):
        self.priority_widget = PriorityWidget()
        if 'recipeset' in kw:
            self.recipeset = kw['recipeset']
        else:
            self.recipeset = None

   
class RecipeWidget(CompoundWidget):
    javascript = []
    css = []
    template = "bkr.server.templates.recipe_widget"
    params = ['recipe']
    member_widgets = ['recipe_tasks_widget']
    recipe_tasks_widget = RecipeTasksWidget()

class PriorityWidget(SingleSelectField):   
   validator = validators.NotEmpty()
   params = ['default','controller'] 
   def __init__(self,*args,**kw): 
       self.options = [] 
       self.field_class = 'singleselectfield' 

   def display(self,obj,value=None,**params):           
       if 'priorities' in params: 
           params['options'] =  params['priorities']       
       else:
           params['options'] = [(elem.id,elem.priority) for elem in TaskPriority.query().all()]
       if isinstance(obj,model.Job):
           if 'id_prefix' in params:
               params['attrs'] = {'id' : '%s_%s' % (params['id_prefix'],obj.id) }
       elif obj:
           if 'id_prefix' in params:
               params['attrs'] = {'id' : '%s_%s' % (params['id_prefix'],obj.id) } 
           try:
               value = obj.priority.id 
           except AttributeError,(e):
               log.error('Object %s passed to display does not have a valid priority: %s' % (type(obj),e))
       return super(PriorityWidget,self).display(value or None,**params)

class UserAlphaNavBar(Widget):
    template = "bkr.server.templates.user_alpha_navbar"
    params = ['letters']

    def __init__(self,letters,*args,**kw):
        self.letters = letters 
