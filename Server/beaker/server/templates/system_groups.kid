<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <table class="list">
  <tr class="list">
   <th class="list">
    <b>Name</b>
   </th>
   <th class="list">
    <b>Display Name</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <tr class="list" py:if="not readonly">
   <td class="list">
    ${display_field_for("group")}
   </td>
   <td class="list">
    &nbsp;
   </td>
   <td class="list">
    ${display_field_for("id")}
    <a class="button" href="javascript:document.${name}.submit();">Add ( + )</a>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="group in groups">
   <td class="list">
    ${group.group_name}
   </td>
   <td class="list">
    ${group.display_name}
   </td>
   <td class="list">
    <a py:if="not readonly" class="button" href="${tg.url('/group_remove', system_id=value_for('id'), group_id=group.group_id)}">Delete ( - )</a>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</form>
