<table id="systemgroups" class="table table-striped table-one-line-per-row" xmlns:py="http://purl.org/kid/ns#">
  <thead>
    <tr>
      <th>Name</th>
      <th>Display Name</th>
      <th>Admin Rights</th>
      <th/>
    </tr>
  </thead>
  <tbody>
    <tr py:if="not readonly">
      <td>
    ${display_field_for("group")}
      </td>
      <td />
      <td />
      <td>
    <form name="${name}" action="${action}" method="POST" onsubmit="populate_form_elements(this); return true;">
     <script src="${tg.url('/static/javascript/magic_forms.js')}"
      type='text/javascript'/>
     ${display_field_for("id")}
     <input type="hidden"
      id="${name}_${group.name}_${group.text_field.name}_hidden"
      name="${group.name}.text" />
     <button class="btn btn-primary" type="submit"><i class="icon-plus"/> Add</button>
    </form>
      </td>
    </tr>
    <tr py:for="group_assoc in group_assocs">
      <?python group = group_assoc.group ?>
      <td>
    ${group.group_name}
      </td>
      <td>
    ${group.display_name}
      </td>
      <td>
   <span py:if="'admin' not in [group.group_name]">
   <span py:if="group_assoc.admin">
     <span id="admin_group_${group.group_id}">Yes
      <a class="btn" py:if="'admin' in tg.identity.groups or can_admin"
       onclick="remove_system_admin('${change_admin_url}', ${group.group_id});return false;"
       href="#"><i class="icon-remove"/> Remove</a>
     </span>
     <span id="non_admin_group_${group.group_id}" style="display:none">No
       <a class="btn" py:if="'admin' in tg.identity.groups or can_admin"
        onclick="add_system_admin('${change_admin_url}', ${group.group_id});return false;"
        href="#"><i class="icon-plus"/> Add</a>
     </span>
   </span>
   <span py:if="not group_assoc.admin">
     <span id="admin_group_${group.group_id}" style="display:none">Yes
      <a class="btn" py:if="'admin' in tg.identity.groups or can_admin"
       onclick="remove_system_admin('${change_admin_url}', ${group.group_id});return false"
       href="#"><i class="icon-remove"/> Remove</a>
     </span>
     <span id="non_admin_group_${group.group_id}">No
      <a class="btn" py:if="'admin' in tg.identity.groups or can_admin"
       onclick="add_system_admin('${change_admin_url}', ${group.group_id});return false"
       href="#"><i class="icon-plus"/> Add</a></span>
   </span>
   </span>
      </td>
      <td>
       <span py:if="not readonly" py:strip='1'>
         ${delete_link.display(dict(system_id=value_for('id'),
             group_id=group.group_id),
             action=tg.url('/group_remove'),
             attrs=dict(class_='link'))}
       </span>
      </td>
    </tr>
  </tbody>
</table>
