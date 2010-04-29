
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
    <b>Admin Rights</b>
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
    &nbsp;
   </td>
   <td class="list">
    ${display_field_for("id")}
    <input type="hidden" id="group_system_id" value="${system_id}" />
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
   <span py:if="'admin' not in [group.group_name]">

   <span py:if="group.can_admin_system(system_id)">
     <span id="admin_group_${group.group_id}">Yes&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin" id="remove_admin_${group.group_id}" href="#">(Remove)</a></span>
     <span id="non_admin_group_${group.group_id}" style="display:none">No&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin"  id="add_admin_${group.group_id}" href="#">(Add)</a></span>
   </span>
   <span py:if="not group.can_admin_system(system_id)">
     <span id="admin_group_${group.group_id}" style="display:none">Yes&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin" id="remove_admin_${group.group_id}" href="#">(Remove)</a></span>
     <span id="non_admin_group_${group.group_id}" >No&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin"  id="add_admin_${group.group_id}" href="#">(Add)</a></span>
   </span>
   </span>
   </td>
   <td class="list">
    <a py:if="not readonly" class="button" href="${tg.url('/group_remove', system_id=value_for('id'), group_id=group.group_id)}">Delete ( - )</a>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</form>
