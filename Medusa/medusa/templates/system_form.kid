<form xmlns:py="http://purl.org/kid/ns#"
    name="${name}"
    action="${tg.url(action)}"
    method="${method}"
    py:attrs="form_attrs" width="100%">

    <div xmlns:py="http://purl.org/kid/ns#">
     ${display_field_for("id")}
     <table class="list">
      <tr class="list">
       <th class="list">
        <b>System Name</b>
       </th>
       <td class="list" colspan="5">
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
       <th class="list">
        <b>Last Checkin</b>
       </th>
       <td class="list">
        ${value_for("date_lastcheckin")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Vendor</b>
       </th>
       <td class="list">
        ${display_field_for("vendor")}
       </td>
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
       <th class="list">
        <b>Condition</b>
       </th>
       <td class="list">
        ${display_field_for("status_id")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        <b>Owner</b>
       </th>
       <td class="list">
        ${value_for("owner")}
        <a py:if="owner_change_text" href="${owner_change}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
       </td>
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
        <a py:if="user_change_text" href="${user_change}?id=${id}">
         <span py:content="user_change_text"/>
        </a>
       </td>
      </tr>
      <tr>
       <th class="list">
        <b>Private</b>
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
       <th class="list">
        <b></b>
       </th>
       <td class="list">
       </td>
      </tr>
      <tr py:if="not readonly">
       <td colspan="6">
        ${field_for("submit").display('Save Changes')}
       </td>
      </tr>
     </table>
    </div>
</form>
