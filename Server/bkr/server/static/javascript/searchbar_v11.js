    SearchBar = function (fields, searchController,operationvalue,
        column_based_controllers,table_search_controllers,searchvalue,keyvaluevalue,
        search_object, date_picker,clone) {
        this.clone = clone
        this.search_object = new SearchObject()
        this.search_object.initialize(search_object)
        this.operationvalue = operationvalue
        this.searchvalue = searchvalue
        if (date_picker) {
            SearchBarForm.datepicker = date_picker
        }
        this.keyvaluevalue = keyvaluevalue
        this.table_controllers = []
        this.column_controller = column_based_controllers
        this.last_table_value = ''
        this.row_identifier = ''
        this.fields = []  
        for (index in fields) {
            field_actual = fields[index].field_id 
            field_complete = field_actual 
            field_name_mod = field_actual.replace(/^(.+?_\d{1,})_(.+)$/, "$2") 
            if (!this.row_identifier) {
                this.row_identifier = field_actual.replace(/^(.+?_\d{1,})_(.+)$/, "$1") 
            }
            field_name = field_name_mod + 'id'
            this[field_name] = field_actual  
            this.fields.push(field_name_mod)

            // this sets a relationship between table/column, and the field that is switched on and off
            // when we select, deselect it
            if (fields[index].column) {
                SearchBarForm.tracking_columns[fields[index].column] = field_name_mod
            } 
        }
     
        for (index in table_search_controllers) {   
             this.table_controllers[index] = table_search_controllers[index]
        }
         
	    this.searchController = searchController;
	    bindMethods(this);
};


SearchBar.prototype.initialize = function() { 
        
        SearchBarForm.searchbar_instances.push(this)
        for (index in this.fields) { 
            field = this.fields[index]
            field_id = this[field+'id']
            this[field+'Field'] = getElement(field_id)
           
            bare_name = field_id.replace(/^(.+?_\d{1,})_(.+)$/,"$2")
            column_controller = this.column_controller[bare_name]
            
            if (column_controller) {
                if (bare_name == 'keyvalue')  
	            updateNodeAttributes(this[field+'Field'], {"onchange": this.keyValueOnChange }); 
            }
            /* Basically what this does is checks whether or not a field of the searchbar
               has been marked to be hidden. If it has, we find the relavent parts of the DOM 
               that need to be hidden (i.e the <td> of the field, and the <th> of it's label).
               We will need to keep track of the number of instances of it
               exist, so as to know whether to hide of display the header
             */
            if ($('#'+this[field+'id']).is('.hide_parent')) { 
               //initialise column_ count to 1 (as at the moment it hasn't been hidden) or ++ it
               if (SearchBarForm.column_count[field]) {
                   SearchBarForm.column_count[field] = ++SearchBarForm.column_count[field]
               } else {
                   SearchBarForm.column_count[field] = 1
               }

               this.hide(field)
            } 
              
        }

        //We will fail right here if we don't set a tableField....
	updateNodeAttributes(this.tableField, {
            "onchange": this.theOnChange
        });
        this.theOnChange()
}

SearchBar.prototype.show = function(field) {
       column_name = field.replace(/^(.+?_\d{1,})_(.+)$/,"$2")
       count = SearchBarForm.column_count[column_name]
       //If we don't have any other instances of this column already, let's display the header for it
       if (count < 1) { 
           label_text = column_name.replace(/^./, column_name.match(/^./)[0].toUpperCase());       
           var th_to_show = $("th:contains('" + label_text + "')").get(0);
           removeElementClass(th_to_show,'hidden')                


            /*Now we need to go through each SearchBar and unhide the td for this column,
             for sake of formatting and appearance
             A few things could be done to make this thing more efficent. First of all we really don't need to be caching the whole SearchBar
             instance, all we really need is the ids and/or elements of the fields.  
            */
            for (index in SearchBarForm.searchbar_instances) {
                searchbar = SearchBarForm.searchbar_instances[index]
                field_element = searchbar[column_name+'Field']      
                to_show = field_element.parentNode.parentNode
                removeElementClass(to_show,'hidden')
            }
       }
         
       //let's show the span.
       span_to_show = getElement(field).parentNode
       removeElementClass(span_to_show,'hidden')

       //and now show the actual field
       td_to_show = getElement(field).parentNode.parentNode
       removeElementClass(td_to_show,'hidden')
       SearchBarForm.column_count[column_name] = ++count
}

SearchBar.prototype.hide = function(field) {
        //this part is to hide the field
        span_to_hide = this[field+'Field'].parentNode
        addElementClass(span_to_hide,'hidden')
        count = SearchBarForm.column_count[field]  
        count-- 
 
        //If we no longer have any of these columns displayed, let's hide the label and td
        if (count < 1) {
            SearchBarForm.hide_others(field)
        }
       
        SearchBarForm.column_count[field] = count
}


SearchBar.prototype.replaceValOptions = function(arg) { 
    val = arg;
    text = arg
    //vals can be an object if we are to specify a particular value for the text of the option field 
    if (isArray(arg)) {
        for(elem in arg) { 
            val = arg[0];
            text = arg[1]; 
        }
    }
    
    if ( val == this.searchvalue ) {
        option = OPTION({"value": val,
                       "selected": true}, text);
    } else {
        option = OPTION({"value": val}, text);
    }
    return option;
}

SearchBar.prototype.replaceKeyValues = function(arg) {    
    if (arg == this.keyvaluevalue) {
        option = OPTION({"value": arg,
                       "selected": true}, arg);
    } else {
        option = OPTION({"value": arg}, arg);
    }
    return option;
}

SearchBar.prototype.replaceOperations = function(arg) {    
    if ( arg == this.operationvalue ) {
        option = OPTION({"value": arg,
                         "selected": true}, arg);
    } else {
        option = OPTION({"value": arg}, arg);
    }
    return option;
}


SearchBar.prototype.replaceKeyValueFields = function(result) {
   replaceChildNodes(this.keyvalueid, map(this.replaceKeyValues,result.keyvals))
   this.keyValueOnChange()

}

SearchBar.prototype.replaceFields = function(result) {
   this.updateSearchVals(result.search_vals) 
   replaceChildNodes(this.operationid, map(this.replaceOperations, result.search_by));
}

SearchBar.prototype.createValueField = function(current, vals) {
    var current_attrs = current.attributes
    var clone_attrs = {}
    var current_attrs_length = current_attrs.length
    for (index = 0;index < current_attrs_length ;index++) {
        var node_name = current_attrs[index].nodeName
        var node_val = current_attrs[index].nodeValue
        // we only need to clone id, name and value
        if ( node_name == 'id' || node_name == 'name' || node_name == 'value')
            clone_attrs[node_name] =node_val
    }
    var table_value_lower = this.tableField.value.toLowerCase()
    for (i in SearchBarForm.datepicker) {
        if (table_value_lower == SearchBarForm.datepicker[i]) {
            clone_attrs['data-provide'] = 'datepicker';
            clone_attrs['data-date-format'] = 'yyyy-mm-dd';
            clone_attrs['data-autoclose'] = 'true';
            clone_attrs['pattern'] = '\\d\\d\\d\\d-\\d\\d-\\d\\d';
            clone_attrs['title'] = 'date in YYYY-MM-DD format';
        }
    }

    if(vals) {//set up drop down menu
        if (!isArray(vals)) {
            var vals = convertObjToArray(vals)
        }
        if (current.nodeName == 'SELECT') {
            //update options and get out of here
            replaceChildNodes(current,map(this.replaceValOptions,vals))
            return [current, clone_attrs]
        }
        var new_dom = SELECT(null,map(this.replaceValOptions, vals))
    } else {
        //We don't want to put the value from out drop down box into our input field
        if (current.nodeName == 'SELECT' || this.clone) {
            delete(clone_attrs['value'])
        } 
        //set up text field
        if (!clone_attrs['type']) {
            clone_attrs['type'] = ['text']
        } else {
            clone_attrs['type'].push('text')
        }

        if (!clone_attrs['class']) {
            clone_attrs['class'] = ['textfield']
        } else {
            clone_attrs['class'].push('textfield')
        }
        var new_dom = INPUT(clone_attrs)

    }

    return [new_dom, clone_attrs]
}

SearchBar.prototype.updateSearchVals = function(vals) {
    var current = getElement(this.valueid)
    var value_field = new Array(2)
    var value_field_data = this.createValueField(current, vals)
    if (value_field_data != undefined && isArray(value_field_data)) {
        var new_attrs = value_field_data.pop()
        var classes_to_add = new_attrs['class']
        delete new_attrs['class']
        var new_dom = value_field_data.pop()
        updateNodeAttributes(new_dom,new_attrs)
        var par = current.parentNode
        replaceChildNodes(par,new_dom)

        //updateNodeAttributes does not work with classes
        for(i in classes_to_add) {
            addElementClass(new_dom,classes_to_add[i])
        }
    }
}

SearchBar.prototype.keyValueOnChange = function(event) {
    cached_data = this.search_object.keyvalue_value(this.keyvalueField.value)
    if (cached_data) {
        this.replaceFields(cached_data)
        return
    }
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "keyvalue_field"     : this.keyvalueField.value};

    controller = this.column_controller['keyvalue']

    var d = loadJSONDoc(controller + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}


SearchBar.prototype.theOnChange = function(event) {
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "table_field"         : this.tableField.value};

    callback = this.replaceFields //default callback
    controller = this.searchController //default controller
   
    /*let's switch off any columns the new value isn't using.
      We do this by having a look at the last column that was used, and basically hiding all the columns
      it was explicitly showing by way of the SearchBarForm.tracking_columns variable
    */
    if (SearchBarForm.tracking_columns[this.last_table_value]) {
        field_to_hide = SearchBarForm.tracking_columns[this.last_table_value]
        this.hide(field_to_hide)
    }
     
    //table_field. Now what we need to do here is have a look at the
    //tracking_column to see if this new table_field needs to switch any columns on
    table_value_lower = this.tableField.value.toLowerCase()
    tracked_column = SearchBarForm.tracking_columns[table_value_lower]
    if (tracked_column) {
        table_field_id = this.tableField.id
        parent_tr_id  = table_field_id.replace(/^(.+?_\d{1,})_(.+)$/,"$1")
        field_to_show = parent_tr_id+'_'+SearchBarForm.tracking_columns[table_value_lower]
        this.show(field_to_show)

    }

    special_controller = this.table_controllers[table_value_lower]
    if (special_controller) {
        controller = special_controller

        /* If you want to specify a particular function to deal with the returned
         * results of the ajax call, do so here..
         */
        if (table_value_lower == 'key/value') {
            params = {}
            callback = this.replaceKeyValueFields
        }
    }

    this.last_table_value = table_value_lower
    //Lets see if we have the value cached locally first
    cached_data = this.search_object.table_value(table_value_lower)
    if (cached_data) {
        callback(cached_data)
    } else {
        var d = loadJSONDoc(controller + "?" + queryString(params));
        d.addCallback(callback);
    }
}

var SearchBarForm = {

    li_count: null,
    li_template: null,

    searchbar_instances : [],
    tracking_columns : [],
    column_count : [],
    operation_defer : ['key/value'],

    removeItem: function(node_id) {
        this_node = document.getElementById(node_id);
        parent_node = this_node.parentNode;
        list_items = SearchBarForm.getChildNodesByAttribute(parent_node, 'tagname', 'TR')
        SearchBarForm.updateVars(parent_node.parentNode);
        if (list_items.length == 1) {
            alert('This item cannot be removed.')
        }
        else {
            // Before we remove the node we need to manage any hidden columns call a hide on it
             
            table_node = document.getElementById(node_id + '_table')
            table_value_lower = table_node.value.toLowerCase()
           
	        indexes_to_delete = []
			for (index in SearchBarForm.searchbar_instances) {
			    row_identifier = SearchBarForm.searchbar_instances[index].row_identifier
				if (row_identifier == node_id) {
				    tracking_field =  SearchBarForm.tracking_columns[table_value_lower]
					if (tracking_field) {
					    SearchBarForm.searchbar_instances[index].hide(tracking_field)
					}
					indexes_to_delete.push(index)          
				}
			}  

			for (index in indexes_to_delete) {
					SearchBarForm.searchbar_instances.splice(indexes_to_delete[index],1) 	
			}                       

            parent_node.removeChild(this_node);
        }
    },

    hide_others : function(field) {
            label_text = field
            label_text = label_text.replace(/^./, label_text.match(/^./)[0].toUpperCase());       
            var th_to_hide = $("th:contains('" + label_text + "')").get(0);
            addElementClass(th_to_hide,'hidden')                

	    /*Now we need to go through each SearchBar and hide the td for this column,
	      for sake of formatting and appearance
	    */
	    for (index in SearchBarForm.searchbar_instances) {
		    searchbar = SearchBarForm.searchbar_instances[index]
	            to_hide = searchbar[field+'Field'].parentNode.parentNode      
                    addElementClass(to_hide,'hidden')
	    }
    },

    getChildNodesByAttribute: function(pnode, identifier, value) {
        new_nodes = new Array;
        nodes = pnode.childNodes;
        for (node_id=0, len=nodes.length; node_id<len; node_id++) {
            node = nodes[node_id];
            if (identifier == 'tagname') {
                if (node && node.tagName == value) {
                    new_nodes.push(node);
                }
            }
            else if (node && node.getAttribute(identifier) == value) {
                new_nodes.push(node);
            }
        }
        return new_nodes;
    },

    updateVars: function(parent_node){
        tbody = SearchBarForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        list_items = SearchBarForm.getChildNodesByAttribute(tbody, 'tagname', 'TR');
        SearchBarForm['li_template'] = list_items[0];
        SearchBarForm['li_count'] = list_items.length
    },

    addItem: function(parent_id) {
        var parent_node = document.getElementById(parent_id);
        SearchBarForm.updateVars(parent_node);
        tbody = SearchBarForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        list_items = SearchBarForm.getChildNodesByAttribute(tbody, 'tagname', 'TR');
        li_clone = SearchBarForm.li_template.cloneNode(true);
        // Fix the labels.
/*        labels = li_clone.getElementsByTagName('LABEL')
        for (node_id=0, len=labels.length; node_id<len; node_id++) {
            label = labels[node_id];
            // Why am I having to check for the node type?
            if (label.nodeType == 1) {
                label.setAttribute('for', label.getAttribute('for').replace(
                    '_0_', '_' + SearchBarForm.li_count + '_'));
            }
        }
*/        // Fix the input values.
        inputs = li_clone.getElementsByTagName('INPUT')
        for (node_id=0, len=inputs.length; node_id<len; node_id++) {
            input = inputs[node_id];
            if (input.nodeType == 1) {
                input.setAttribute('id', input.getAttribute('id').replace(
                    /_\d{1,}_/, '_' + SearchBarForm.li_count + '_'));
                if (input.getAttribute('name'))
                {
                    input.setAttribute('name', input.getAttribute('name').replace(
                        /\-\d{1,}/, '-' + SearchBarForm.li_count));
                }

                if (input.getAttribute('type') == 'button')
                {
                    input.setAttribute('value', input.getAttribute('value'))
                }
                else
                {
                    input.value = '';
                }
            }
        }

        inputs = li_clone.getElementsByTagName('SELECT')
        for (node_id=0, len=inputs.length; node_id<len; node_id++) {
            input = inputs[node_id];
            if (input.nodeType == 1) {
                input.setAttribute('id', input.getAttribute('id').replace(
                    /_\d{1,}_/, '_' + SearchBarForm.li_count + '_'));
                input.setAttribute('name', input.getAttribute('name').replace(
                    /\-\d{1,}/, '-' + SearchBarForm.li_count));
                input.value = '';
            }
        }
        li_clone.setAttribute('id', li_clone.getAttribute('id').replace(
            '_0', '_' + SearchBarForm.li_count))
        // Add a remove link.
        child_tds = li_clone.getElementsByTagName('td');
        last_td = child_tds[child_tds.length-1];
        a_clone = last_td.getElementsByTagName('A')[0];
        href_text = "javascript:SearchBarForm.removeItem('" + li_clone.getAttribute('ID') + "')";
        a_clone.setAttribute('href', href_text);
        // Finally.
        tbody = SearchBarForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        tbody.appendChild(li_clone);

        fields_for_newsearchbar = []
        $('#'+li_clone.id+' span').each( function() { 
            children = $(this).children().each( function() {
                fields_for_newsearchbar.push({'field_id': $(this).attr('id'), 'name': $(this).attr('name').replace(/.+?\-\d{1,}\.(.+)?/, "$1") }) 
            });
        });
       
        searchbar_instance = SearchBarForm.searchbar_instances.pop()
        SearchBarForm.searchbar_instances.push(searchbar_instance)  

        new_search = new SearchBar(fields_for_newsearchbar, searchbar_instance.searchController,'', 
            searchbar_instance.column_controller,searchbar_instance.table_controllers,undefined,
            undefined,undefined,undefined,true);
 
        new_search.initialize() 
  
        // Focus
        if(li_clone.getElementsByTagName('input')[0])
            li_clone.getElementsByTagName('INPUT')[0].focus()
        else
            li_clone.getElementsByTagName('select')[0].focus()

        SearchBarForm['li_count'] = SearchBarForm.li_count + 1;
    }
}

// Not specifically part of appendable_form_field, but used by the customised version of this form
function typeChanged(obj) {
    var parent = obj.parentNode.parentNode.parentNode;
    var preference = parent.getElementsByTagName("input")[1];
    var type = obj.value;
    if (type == 'MX') {
        preference.style.visibility = "visible";
    }
    else {
        preference.style.visibility = "hidden";
    }
}


function convertObjToArray(obj) {
    var size = Object.size(obj);
    var new_array = new Array(size);
    var i = 0;
    for(elem in obj){
        new_array[i] = [elem,obj[elem]];
        i++
    }    
    return new_array;
}


function JSONStringifyObj(obj) {
    for (index in obj) {
            json_stringified = json_stringified + JSONStringifyElem(obj[index])
            json_stringified = json_stringified + ','
        }
        json_stringified_length = json_stringified.length
        result = json_stringified.slice(0,json_stringified_length -1 )
        return result
}


function JSONStringifyElem(obj) {
   var json_text = ''
   for (elem in obj) {
       json_text = json_text + "'"+elem+"':'"+obj[elem]+"',"
   }
   json_length = json_text.length
   json_text = json_text.slice(0,json_length-1)
   json_text = '{'+json_text
   json_text = json_text +'}'
   return json_text
}


function isArray(obj) {
if (obj.constructor.toString().indexOf('Array') == -1)
    return false;
else
    return true;
}

Object.size = function(obj) {
    var size =0, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) size++;
    }
    return size;
};

