<table class="table table-striped table-one-line-per-row table-hover" xmlns:py="http://purl.org/kid/ns#">
  <thead>
    <tr>
      <th>Key</th>
      <th>Value</th>
      <th/>
    </tr>
  </thead>
  <tbody>
    <tr py:if="not readonly">
      <td>
    ${display_field_for("key_name")}
      </td>
      <td>
    ${display_field_for("key_value")}
      </td>
      <td>
    <form name="${name}" action="${action}" method="POST" onsubmit="populate_form_elements(this); return true;">
     <script src="${tg.url('/static/javascript/magic_forms.js')}"
      type='text/javascript'/>
     ${display_field_for("id")}
     <input type='hidden' id='${name}_${key_name.name}_hidden'
      name='${key_name.name}' />
     <input type='hidden' id='${name}_${key_value.name}_hidden'
      name='${key_value.name}' />
     <button class="btn btn-primary" type="submit"><i class="fa fa-plus"/> Add</button>
   </form>
   </td>
  </tr>
    <tr py:for="key_value in key_values">
      <td>
    ${key_value.key.key_name}
      </td>
      <td>
    ${key_value.key_value}
      </td>
      <td>
    <span py:strip='1' py:if='not readonly'>
     ${delete_link(dict(key_type=key_value.key_type,
         system_id=value_for('id'),
         key_value_id=key_value.id),
         action=tg.url('/key_remove'))}
    </span>
      </td>
    </tr> 
  </tbody>
</table>
