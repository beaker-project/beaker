SearchBar = function (tableid, columnid, searchController, columnvalue) {
	this.tableid = tableid;
	this.tableField = null;
        this.columnid = columnid;
	this.columnField = null;
        this.columnvalue = columnvalue;
	this.searchController = searchController;
	bindMethods(this);
};

SearchBar.prototype.initialize = function() {
	this.tableField = getElement(this.tableid);
	this.columnField = getElement(this.columnid);
	updateNodeAttributes(this.tableField, {
            "onchange": this.theOnChange
        });
        this.theOnChange()
}

SearchBar.prototype.replaceOptions = function(arg) {
    if ( arg == this.columnvalue ) {
        option = OPTION({"value": arg,
                       "selected": true}, arg);
    } else {
        option = OPTION({"value": arg}, arg);
    }
    return option;
}

SearchBar.prototype.replaceFields = function(result) {
   replaceChildNodes(this.columnid, map(this.replaceOptions, result.fields));
}

SearchBar.prototype.theOnChange = function(event) {
    var params = {"tg_format"          : "json",
                  "tg_random"          : new Date().getTime(),
                  "table_name"         : this.tableField.value};

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
        searchbar = li_clone.id + " = new SearchBar('" + li_clone.id + "_table', '" + li_clone.id + "_column', '/get_fields', '');" + li_clone.id + ".initialize();";
        eval(searchbar);
        // Focus
        li_clone.getElementsByTagName('INPUT')[0].focus()
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
