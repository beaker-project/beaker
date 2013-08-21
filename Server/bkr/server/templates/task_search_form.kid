<div xmlns:py="http://purl.org/kid/ns#" style="vertical-align: top;">
<script type='text/javascript'>

            function task_search_before() {
                $('#task_items').empty()
                AjaxLoader.prototype.add_loader('task_items')
            }

            function task_search_complete() {
                AjaxLoader.prototype.remove_loader('task_items') 
            }

</script>
<form 
    name="${use_name and name or None}"
    id="${not use_name and name or None}"
    action="${tg.url(action)}"
    method="${method}"
    py:attrs="form_attrs"
>
<?python
    vfields = []
    for field in fields:
        if not hidden.get(field.name):
            vfields.append(field)
?>
    <div py:if="hidden_fields" style="display:none">
        <div py:for="field in hidden_fields"
            py:replace="field.display(value_for(field), **params_for(field))"
        />
    </div>
    <table border="0" cellspacing="0" cellpadding="2" py:attrs="table_attrs">
        <tr py:for="i in range(0,len(vfields)/4 + len(vfields)%4)">
            <th py:for="j in range((i*4),4+(i*4))">
              <span py:if="j.__cmp__(len(vfields)) == -1">
                <label class="fieldlabel" for="${vfields[j].field_id}" py:content="vfields[j].label" />
              </span>
            </th>
           <tr>
           </tr>
            <td py:for="j in range((i*4),4+(i*4))">
              <span py:if="j.__cmp__(len(vfields)) == -1">
                <span py:replace="vfields[j].display(value_for(vfields[j]), **params_for(vfields[j]))" />
                <span py:if="error_for(vfields[j])" class="fielderror" py:content="error_for(vfields[j])" />
                <span py:if="vfields[j].help_text" class="fieldhelp" py:content="vfields[j].help_text" />
              </span>
            </td>
        </tr>
        <tr>
            <td>&#160;</td>
            <td>
                <button type="submit" class="btn">${submit_text}</button>
            </td>
        </tr>
    </table>
</form>
</div>
