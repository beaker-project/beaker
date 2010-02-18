<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 &nbsp;&nbsp;
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
    ${display_field_for("id")}
    <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="key_value in key_values_int">
   <td class="list">
    ${key_value.key.key_name}
   </td>
   <td class="list">
    ${key_value.key_value}
   </td>
   <td class="list"><a py:if="not readonly" class="button" href="${tg.url('/key_remove', key_type='int', system_id=value_for('id'), key_value_id=key_value.id)}">Delete ( - )</a></td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr> 
  <tr class="list" bgcolor="${row_color}" py:for="key_value in key_values_string">
   <td class="list">
    <!--${key_value.key.key_name} -->
   </td>
   <td class="list">
    ${key_value.key_value}
   </td>
   <td class="list"><a py:if="not readonly" class="button" href="${tg.url('/key_remove', key_type='string', system_id=value_for('id'), key_value_id=key_value.id)}">Delete ( - )</a></td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr> 
 </table>
</form>
