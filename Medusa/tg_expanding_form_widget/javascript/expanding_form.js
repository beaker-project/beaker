
/* Based on dynwidget by Randall Smith */

var ExpandingForm = {

    li_count: null,
    li_template: null,

    removeItem: function(node_id) {
        this_node = document.getElementById(node_id);
        parent_node = this_node.parentNode;
        list_items = ExpandingForm.getChildNodesByAttribute(parent_node, 'tagname', 'TR')
        ExpandingForm.updateVars(parent_node.parentNode);
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
        tbody = ExpandingForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        list_items = ExpandingForm.getChildNodesByAttribute(tbody, 'tagname', 'TR');
        ExpandingForm['li_template'] = list_items[0];
        ExpandingForm['li_count'] = list_items.length
    },

    addItem: function(parent_id) {
        var parent_node = document.getElementById(parent_id);
        ExpandingForm.updateVars(parent_node);
        tbody = ExpandingForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        list_items = ExpandingForm.getChildNodesByAttribute(tbody, 'tagname', 'TR');
        li_clone = ExpandingForm.li_template.cloneNode(true);
        // Fix the labels.
/*        labels = li_clone.getElementsByTagName('LABEL')
        for (node_id=0, len=labels.length; node_id<len; node_id++) {
            label = labels[node_id];
            // Why am I having to check for the node type?
            if (label.nodeType == 1) {
                label.setAttribute('for', label.getAttribute('for').replace(
                    '_0_', '_' + ExpandingForm.li_count + '_'));
            }
        }
*/        // Fix the input values.
        inputs = li_clone.getElementsByTagName('INPUT')
        for (node_id=0, len=inputs.length; node_id<len; node_id++) {
            input = inputs[node_id];
            if (input.nodeType == 1) {
                input.setAttribute('id', input.getAttribute('id').replace(
                    '_0_', '_' + ExpandingForm.li_count + '_'));
                if (input.getAttribute('name'))
                {
                    input.setAttribute('name', input.getAttribute('name').replace(
                        '-0', '-' + ExpandingForm.li_count));
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
                    '_0_', '_' + ExpandingForm.li_count + '_'));
                input.setAttribute('name', input.getAttribute('name').replace(
                    '-0', '-' + ExpandingForm.li_count));
                input.value = '';
            }
        }
        li_clone.setAttribute('id', li_clone.getAttribute('id').replace(
            '_0', '_' + ExpandingForm.li_count))
        // Add a remove link.
        child_tds = li_clone.getElementsByTagName('td');
        last_td = child_tds[child_tds.length-1];
        a_clone = last_td.getElementsByTagName('A')[0];
        href_text = "javascript:ExpandingForm.removeItem('" + li_clone.getAttribute('ID') + "')";
        a_clone.setAttribute('href', href_text);
        /*
        link_li = document.createElement('LI');
        link_a = document.createElement('A');
        href_text = "javascript:ExpandingForm.removeItem('" + li_clone.getAttribute('ID') + "')";
        link_a.setAttribute('href', href_text);
        /*
        text = 'Remove (-)';
        link_text = document.createTextNode(text);
        link_a.appendChild(link_text);
        link_li.appendChild(link_a);
        ul.appendChild(link_li);
        */
        // Finally.
        tbody = ExpandingForm.getChildNodesByAttribute(parent_node, 'tagname', 'TBODY')[0];
        tbody.appendChild(li_clone);
        // Focus
        li_clone.getElementsByTagName('INPUT')[0].focus()
        ExpandingForm['li_count'] = ExpandingForm.li_count + 1;
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
