<form xmlns:py="http://purl.org/kid/ns#"
  name="${name}"
  action="${tg.url(action)}"
  method="${method}" width="100%">

    <div xmlns:py="http://purl.org/kid/ns#">
     ${display_field_for("id")}
     <table class="list">
      <tr class="list">
       <th class="list">
        <b>System Name</b>
       </th>
       <td class="list" colspan="3">
        ${display_field_for("fqdn")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Date Created</b>
       </th>
       <td class="list">
        ${value_for("date_added")}
       </td>
       <th class="list">
        <b>Last Modification</b>
       </th>
       <td class="list">
        ${value_for("date_modified")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Last Checkin</b>
       </th>
       <td class="list">
        ${value_for("date_lastcheckin")}
       </td>
       <th class="list">
        <b>Vendor</b>
       </th>
       <td class="list">
        ${display_field_for("vendor")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Lender</b>
       </th>
       <td class="list">
        ${display_field_for("lender")}
       </td>
       <th class="list">
        <b>Model</b>
       </th>
       <td class="list">
        ${display_field_for("model")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Serial Number</b>
       </th>
       <td class="list">
        ${display_field_for("serial")}
       </td>
       <th class="list">
        <b>Location</b>
       </th>
       <td class="list">
        ${display_field_for("location")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Condition</b>
       </th>
       <td class="list">
        ${display_field_for("status_id")}
       </td>
       <th class="list">
        <b>Owner</b>
       </th>
       <td class="list">
        ${value_for("owner")}
        <a py:if="owner_change_text" href="${tg.url(owner_change)}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Shared</b>
       </th>
       <td class="list">
        ${display_field_for("shared")}
       </td>
       <th class="list">
        <b>Current User</b>
       </th>
       <td class="list">
        ${value_for("user")}
        <a py:if="user_change_text" href="${tg.url(user_change)}?id=${id}">
         <span py:content="user_change_text"/>
        </a>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Secret (NDA)</b>
       </th>
       <td class="list">
        ${display_field_for("private")}
       </td>
       <th class="list">
        <b>Type</b>
       </th>
       <td class="list">
        ${display_field_for("type_id")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Lab Controller</b>
       </th>
       <td class="list">
        ${display_field_for("lab_controller_id")}
       </td>
       <th class="list">
        <b>Mac Address</b>
       </th>
       <td class="list">
        ${display_field_for("mac_address")}
       </td>
      </tr>
      <tr py:if="not readonly">
       <td colspan="4">
        <a class="button" href="javascript:document.${name}.submit();">Save Changes</a>
       </td>
      </tr>
     </table>
    </div>
</form>
