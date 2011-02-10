<form xmlns:py="http://purl.org/kid/ns#"
 name="${name}"
 action="${tg.url(action)}"
 method="${method}" width="100%">
 <table class="list">
  <tr class="list">
   <th class="list">
    <b>Lab Controller</b>
   </th>
   <th class="list">
    <b>Location</b>
   </th>
   <th class="list">
    <b>&nbsp;</b>
   </th>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="lab_controller in lab_controllers">
   <td class="list">
    ${lab_controller.lab_controller.fqdn}
   </td>
   <td class="list">
    ${lab_controller.tree_path}
   </td>
   <td class="list">
    <a py:if="not readonly" class="button" href="${tg.url('./lab_controller_remove', id=value_for('id'), lab_controller=lab_controller.lab_controller.fqdn)}">Delete ( - )</a>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</form>
