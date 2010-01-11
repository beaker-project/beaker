<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
$(document).ready(function(){ 
    $("#form_status_id").change(function() 
    { 
        if ($('#form_status_id :selected').text() == 'Broken' || $('#form_status_id :selected').text() == 'Removed') {
             $('#condition_report_row').removeClass('hidden')
        };
        if ($('#form_status_id :selected').text() == 'Working') {
             $('#condition_report_row').addClass('hidden')
        } 
    });
    if ($('#form_status_id :selected').text() == 'Working') {
         $('#condition_report_row').addClass('hidden')
    } 
});
</script>
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
      <tr class="list" id="condition_report_row">
       <th class="list" >
        <b>Condition Report</b>
       </th>
       <td class="list"> 
        ${display_field_for("status_reason")}
       </td>
      </tr>
      <tr class="list"> 
       <th class="list">
        <b>Shared</b>
       </th>
       <td class="list">
        <span py:if="value_for('fqdn')">
         ${display_field_for("shared")}
        </span>
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
        <b>Loaned To</b>
       </th>
       <td class="list">
        ${value_for("loaned")}
        <a py:if="loan_text" href="${tg.url(loan_change)}?id=${id}">
         <span py:content="loan_text"/>
        </a>
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
      <tr class="list">
       <th class="list">
        <b>Type</b>
       </th>
       <td class="list">
        ${display_field_for("type_id")}
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
</div>
