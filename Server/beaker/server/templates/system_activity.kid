<div xmlns:py="http://purl.org/kid/ns#">
 <table class="list">
  <tr class="list">
   <th class="list">user</th>
   <th class="list">Via</th>
   <th class="list">Date</th>
   <th class="list">Property</th>
   <th class="list">Action</th>
   <th class="list">Old Value</th>
   <th class="list">New Value</th>
  </tr>
  <?python row_color = "#FFFFFF" ?>
  <tr class="list" bgcolor="${row_color}" py:for="act in system.activity[:30]">
   <td class="list">${act.user}</td>
   <td class="list">${act.service}</td>
   <td class="list">${act.created}</td>
   <td class="list">${act.field_name}</td>
   <td class="list">${act.action}</td>
   <td class="list">${act.old_value}</td>
   <td class="list">${act.new_value}</td>
   <?python row_color = (row_color == "#f1f1f1") and "#FFFFFF" or "#f1f1f1" ?>
  </tr>
 </table>
</div>
