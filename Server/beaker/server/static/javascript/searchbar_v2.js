SearchBar = function (tableid, operationid,valueid, searchController, operationvalue,searchvalue) {
	this.tableid = tableid;
	this.tableField = null;
        this.operationvalue = operationvalue;
        this.operationid = operationid;
        this.operationField = null;
        this.valueField = null;
        this.searchvalue = searchvalue
        this.valueid = valueid;
	this.searchController = searchController;
	bindMethods(this);
};

SearchBar.prototype.initialize = function() {
	this.tableField = getElement(this.tableid);
	this.operationField = getElement(this.operationid);
        this.valueField = getElement(this.valueid);
	updateNodeAttributes(this.tableField, {
            "onchange": this.theOnChange
        });
        this.theOnChange()
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

SearchBar.prototype.replaceOptions = function(arg) {
    if ( arg == this.operationvalue ) {
        option = OPTION({"value": arg,
                       "selected": true}, arg);
    } else {
        option = OPTION({"value": arg}, arg);
    }
    return option;
}


SearchBar.prototype.replaceFields = function(result) {
   this.updateSearchVals(result.search_vals) 
   replaceChildNodes(this.operationid, map(this.replaceOptions, result.search_by));
}

SearchBar.prototype.updateSearchVals = function(vals) {
  current = getElement(this.valueid)
  current_attrs = current.attributes
  par = current.parentNode 

  clone_attrs = {}
  current_attrs_length = current_attrs.length
  for (index = 0;index < current_attrs_length ;index++) {
      node_name = current_attrs[index].nodeName
      node_val = current_attrs[index].nodeValue
      if ( node_name != 'type' &&  node_name != 'class') 
          clone_attrs[node_name] =node_val
  }
  
  if(vals) {//set up drop down menu
      //Do we need to convert this to an array ?
      if (!isArray(vals)) {
          vals = convertObjToArray(vals)
      }
      if (current.nodeName == 'SELECT') {
          //update options and get out of here
          replaceChildNodes(current,map(this.replaceValOptions,vals))
          return
      }
      new_dom = SELECT(null,map(this.replaceValOptions, vals)) 
      extra_attrs = {}
     
  } else {
     //We don't want to put the value from out drop down box into our input field
     delete(clone_attrs['value'])
     //set up text field
     if (current.nodeName == 'INPUT')
         return //leave and walk away, we are already a text field 
     new_dom = INPUT(clone_attrs)
     extra_attrs = {'type': 'text','class':'textfield'}
     
  }
 
  //JS nor MochiKit have a hash.merge() function ?? 
  updateNodeAttributes(new_dom,clone_attrs)
  updateNodeAttributes(new_dom,extra_attrs)
 
  replaceChildNodes(par,new_dom)
}

SearchBar.prototype.theOnChange = function(event) {
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "table_field"         : this.tableField.value};

    var d = loadJSONDoc(this.searchController + "?" + queryString(params));
    d.addCallback(this.replaceFields);
}

var SearchBarForm = {

    li_count: null,
    li_template: null,

    removeItem: function(node_id) {
        this_node = document.getElementById(node_id);
        parent_node = this_node.parentNode;
        list_items = SearchBarForm.getChildNodesByAttribute(parent_node, 'tagname', 'TR')
        SearchBarForm.updateVars(parent_node.parentNode);
        if (list_items.length == 1) {
            alert('This item cannot be removed.')
        }
        else {
            parent_node.removeChild(this_node);
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
                    '_0_', '_' + SearchBarForm.li_count + '_'));
                if (input.getAttribute('name'))
                {
                    input.setAttribute('name', input.getAttribute('name').replace(
                        '-0', '-' + SearchBarForm.li_count));
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
                    '_0_', '_' + SearchBarForm.li_count + '_'));
                input.setAttribute('name', input.getAttribute('name').replace(
                    '-0', '-' + SearchBarForm.li_count));
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
        // This is evil.  I need to figure out these values from the dom.
        searchbar = li_clone.id + " = new SearchBar('" + li_clone.id + "_table','" + li_clone.id + "_operation','" + li_clone.id + "_value', '/get_search_options', '','');" + li_clone.id + ".initialize();";
        eval(searchbar);
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

