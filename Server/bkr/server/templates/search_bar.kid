<div xmlns:py="http://purl.org/kid/ns#">
<form
    id="simpleform"
    name="${name}_simple"
    action="${action}"
    method="${method}"
    class="form-search"
    py:attrs="form_attrs" 
    style="display:${simple}"
>
<div><a id="showadvancedsearch" href="#">Show Search Options</a></div>
<span py:for="hidden in extra_hiddens or []">
    <input type='hidden' id='${hidden[0]}' name='${hidden[0]}' value='${hidden[1]}' />
</span> 
<input type="text" name="simplesearch" value="${simplesearch}" class="search-query"/>
<button type="submit" class="btn">${simplesearch_label}</button>

<div py:if="quickly_searches" class="btn-group">
  <span py:for="quickly_search in quickly_searches" py:strip="True">
    ${button_widget.display(value=quickly_search[1],options=dict(label=quickly_search[0]))}
  </span>
</div>
</form>
<form 
    id="searchform"
    name="${name}"
    action="${action}"
    method="${method}"
    py:attrs="form_attrs"
    style="display:${advanced}"
>
<a id="hideadvancedsearch" href="#">Hide Search Options</a>
<span py:for="hidden in extra_hiddens or []">
    <input type='hidden' id='${hidden[0]}' name='${hidden[0]}' value='${hidden[1]}' />
</span> 
    <table>
    <tr>
    <td>
    <table id="${field_id}">
    <thead>
    <tr> 
      <th py:for="field in fields" py:content="field.label" />
    </tr>
    </thead> 
    <tbody>
    <tr py:for="repetition in repetitions"
        class="${field_class}"
        id="${field_id}_${repetition}">
    <script language="JavaScript" type="text/JavaScript">

        ${field_id}_${repetition} = new SearchBar(
                ${tg.to_json(fields)}, ${tg.to_json(search_controller)},
                ${tg.to_json(value_for('operation'))}, ${extra_callbacks_stringified},
                ${table_search_controllers_stringified},
                ${tg.to_json(value_for('value'))}, ${tg.to_json(value_for('keyvalue'))},
                ${search_object}, ${date_picker}, false);
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
        <a class="btn"
        href="javascript:SearchBarForm.removeItem('${field_id}_${repetition}')"><i class="fa fa-times"/> Remove</a>
    </td>
    </tr>
    </tbody>
    </table></td><td>
      <button class="btn btn-primary" type="submit">Search</button>
    </td>

    </tr>
    <tr>
    <td colspan="2">
      <a id="doclink" class="btn"
         href="javascript:SearchBarForm.addItem('${field_id}');"><i class="fa fa-plus"/> Add</a>
    </td>
    </tr>
    </table>

<a py:if="enable_custom_columns" id="customcolumns" href="#">Toggle Result Columns</a> 
<div style='display:none'  id='selectablecolumns'>
    <ul class="unstyled">
    <li py:if="col_options" py:for="value,desc in col_options">
      <label>
        <input py:if="col_defaults.get(value)" type="checkbox" name = "${field_id}_column_${value}" id="${field_id}_column_${value}" value="${value}" checked='checked' />
        <input py:if="not col_defaults.get(value)" type="checkbox" name = "${field_id}_column_${value}" id="${field_id}_column_${value}" value="${value}" />
        ${desc}
      </label>
    </li>  
    </ul>
<a style='margin-left:10px' id="selectnone" href="#">Select None</a>
<a style='margin-left:10px' id="selectall" href="#">Select All</a>
<a style='margin-left:10px' id="selectdefault" href="#">Select Default</a>
</div> 
</form>
<script type="text/javascript">
$(document).ready(function() {
    $('#showadvancedsearch').click(function () {
        $('#searchform').show('slow');
        $('#simpleform').hide('slow');
        return false;
    });
    $('#hideadvancedsearch').click(function () {
        $('#searchform').hide('slow');
        $('#simpleform').show('slow');
        return false;
    });
    $('#customcolumns').click(function () {
        $('#selectablecolumns').toggle('slow');
        return false;
    });
    $('#selectnone').click(function () {
        $("input[name *= 'systemsearch_column_']").prop('checked', false);
        return false;
    });
    $('#selectall').click(function () {
        $("input[name *= 'systemsearch_column_']").prop('checked', true);
        return false;
    });
    $('#selectdefault').click(function () {
        $("input[name *= 'systemsearch_column_']").each(function () {
            select_only_default($(this));
        });
        return false;
    });

    function select_only_default(obj) {
        var defaults = ${default_result_columns}
        var current_item = obj.val()
        var the_name = 'systemsearch_column_'+current_item
            if (defaults[current_item] == 1) {
                $("input[name = '"+the_name+"']").prop('checked', true);
            } else {
                $("input[name = '"+the_name+"']").prop('checked', false);
            }
        }
    });


</script>
</div>
