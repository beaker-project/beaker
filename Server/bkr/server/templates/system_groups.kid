<span xmlns:py="http://purl.org/kid/ns#" py:strip="1">
 <table id='systemgroups' class="list" xmlns:py="http://purl.org/kid/ns#" width='100%'>
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
    <form name="${name}" action="${tg.url(action)}" method="POST">
     <script src="${tg.url('/static/javascript/magic_forms.js')}"
      type='text/javascript'/>
     ${display_field_for("id")}
     <input type="hidden"
      id="${name}_${group.name}_${group.text_field.name}_hidden"
      name="${group.name}.text" />
     <a onclick='populate_form_elements(this.parentNode);return true;'
      href="javascript:document.${name}.submit();">Add ( + )</a>
    </form>
   </td>
  </tr>
  <?python row_color = "#f1f1f1" ?>
  <tr class="list" bgcolor="${row_color}" py:for="group_assoc in group_assocs">
   <?python group = group_assoc.group ?>
   <td class="list">
    ${group.group_name}
   </td>
   <td class="list">
    ${group.display_name}
   </td>
   <td class="list">  
   <span py:if="'admin' not in [group.group_name]">

   <span py:if="group_assoc.admin">
     <span id="admin_group_${group.group_id}">Yes&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin" id="remove_admin_${group.group_id}" href="#">(Remove)</a></span>
     <span id="non_admin_group_${group.group_id}" style="display:none">No&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin"  id="add_admin_${group.group_id}" href="#">(Add)</a></span>
   </span>
   <span py:if="not group_assoc.admin">
     <span id="admin_group_${group.group_id}" style="display:none">Yes&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin" id="remove_admin_${group.group_id}" href="#">(Remove)</a></span>
     <span id="non_admin_group_${group.group_id}" >No&nbsp;<a py:if="'admin' in tg.identity.groups or can_admin"  id="add_admin_${group.group_id}" href="#">(Add)</a></span>
   </span>
   </span>
   </td>
   <td class="list">
       <span py:if="not readonly" py:strip='1'>
         ${delete_link.display(dict(system_id=value_for('id'),
             group_id=group.group_id),
             action=tg.url('/group_remove'),
             attrs=dict(class_='link'))}
       </span>
   </td>
    <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</span>
