<div xmlns="http://www.w3.org/1999/xhtml" xmlns:py="http://purl.org/kid/ns#"
     py:strip="1">
<a id='loan-settings' href="#" onclick="show_loan_actions(); return false;" class="btn btn-mini">Loan Settings</a>
<script type='text/javascript'>
    function show_loan_actions() {
        $('#${name}').attr('title', 'Loan').dialog({
            resizable: false,
            minWidth: 200,
            minHeight: 100,
            height: 'auto',
            width: 'auto',
            modal: true,});
     }
</script>
<div name="${name or None}"
  id="${name or None}"
  class="tableform"
  py:attrs="attrs" >
  <div py:if="hidden_fields" style="display:none">
    <div py:for="field in hidden_fields"
      py:replace="field.display(value_for(field), **params_for(field))" />
    </div>
    <table border="0"
      cellspacing="0"
      cellpadding="2"
      id='update-table'
      py:attrs="table_attrs">
      <tr py:for="i, field in enumerate(fields)" class="${i % 2 and 'odd' or 'even'}">
        <th>
          <label class="fieldlabel" for="${field.field_id}" py:content="field.label" />
        </th>
        <td>
          <span py:replace="field.display(value_for(field),
            **params_for(field))" />
          <span py:if="error_for(field)" class="fielderror" py:content="error_for(field)" />
          <span py:if="field.help_text" class="fieldhelp" py:content="field.help_text" />
        </td>
      </tr>
      <tr>
        <td>&#160;</td>
        <td py:content="update_loan.display()" />
      </tr>
      <tr>
        <td>&#160;</td>
        <td py:content="return_loan.display()" />
      </tr>
    </table>
  </div>
</div>
