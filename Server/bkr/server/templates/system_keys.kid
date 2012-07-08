<span xmlns:py="http://purl.org/kid/ns#" py:strip='1'>
 <table class="list">
  <tr class="list">
   <th class="list">
    <b>Key</b>
   </th>
   <th class="list">
    <b>Value</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <tr class="list" py:if="not readonly">
   <td class="list">
    ${display_field_for("key_name")}
   </td>
   <td class="list">
    ${display_field_for("key_value")}
   </td>
   <td class="list">
    <form name="${name}" action="${tg.url(action)}" method="POST">
     <script src="${tg.url('/static/javascript/magic_forms.js')}"
      type='text/javascript'/>
     ${display_field_for("id")}
     <input type='hidden' id='${name}_${key_name.name}_hidden'
      name='${key_name.name}' />
     <input type='hidden' id='${name}_${key_value.name}_hidden'
      name='${key_value.name}' />
     <a onclick='populate_form_elements(this.parentNode);return true;'
      href="javascript:document.${name}.submit();">Add ( + )</a>
   </form>
   </td>
  </tr>
  <?python
    row_color = "#f1f1f1"
  ?>
  <tr class="list" bgcolor="${row_color}" py:for="key_value in key_values">
   <td class="list">
    ${key_value.key.key_name}
   </td>
   <td class="list">
    ${key_value.key_value}
   </td>
   <td class="list">
    <span py:strip='1' py:if='not readonly'>
     ${delete_link(dict(key_type=key_value.key_type,
         system_id=value_for('id'),
         key_value_id=key_value.id),
         attrs=dict(class_='link'),
         action=tg.url('/key_remove'))}
    </span>
   </td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr> 
 </table>
</span>
