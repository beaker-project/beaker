<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
$(document).ready(function(){ 
    $("#form_status").change(function() {
        if ($('#form_status :selected').text() == 'Broken' || $('#form_status :selected').text() == 'Removed') {
             $('#condition_report_row').removeClass('hidden')
        };
        if ($('#form_status :selected').text() == 'Manual' || $('#form_status :selected').text() == 'Automated') {
             $('#condition_report_row').addClass('hidden')
        } 
    });

    if ($('#form_status :selected').text() == 'Manual' || $('#form_status :selected').text() == 'Automated') {
         $('#condition_report_row').addClass('hidden')
    } 
});
</script>
<label py:def="label_for(field_name)"
       for="${field_for(field_name).field_id}"
       title="${getattr(field_for(field_name), 'help_text', '')}">
    ${field_for(field_name).label}
</label>
<form xmlns:py="http://purl.org/kid/ns#"
  name="${name}"
  action="${tg.url(action)}"
  method="${method}" width="100%">

    <div xmlns:py="http://purl.org/kid/ns#">
     ${display_field_for("id")}
     <table class="list">
      <tr class="list">
       <th class="list">
        ${label_for('fqdn')}
       </th>
       <td class="list" colspan="3">
        ${display_field_for("fqdn")}
        <br/><span py:if="error_for('fqdn')" class="fielderror" py:content="error_for('fqdn')" />
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('date_added')}
       </th>
       <td class="list">
        <span class="datetime">${value_for("date_added")}</span>
       </td>
       <th class="list">
        ${label_for('date_modified')}
       </th>
       <td class="list">
        <span class="datetime">${value_for("date_modified")}</span>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('date_lastcheckin')}
       </th>
       <td class="list">
        <span class="datetime">${value_for("date_lastcheckin")}</span>
       </td>
       <th class="list">
        ${label_for('vendor')}
       </th>
       <td class="list">
        ${display_field_for("vendor")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('lender')}
       </th>
       <td class="list">
        ${display_field_for('lender')}
       </td>
       <th class="list">
        ${label_for('model')}
       </th>
       <td class="list">
        ${display_field_for("model")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('serial')}
       </th>
       <td class="list">
        ${display_field_for("serial")}
       </td>
       <th class="list">
        ${label_for('location')}
       </th>
       <td class="list">
        ${display_field_for("location")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('status')}
       </th>
       <td class="list">
        ${display_field_for("status")}
        <a href="${tg.url('/report_problem/', system_id=id)}">(Report problem)</a>
       </td>
       <th class="list">
        ${label_for('owner')}
       </th>
       <td class="list">
        ${owner_email_link}
        <a py:if="owner_change_text" href="${tg.url(owner_change)}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
       </td>
      </tr>
      <tr class="list" id="condition_report_row">
       <th class="list" >
        ${label_for('status_reason')}
       </th>
       <td class="list"> 
        ${display_field_for("status_reason")}
       </td>
      </tr>
      <tr class="list"> 
       <th class="list">
        ${label_for('shared')}
       </th>
       <td class="list">
        <span py:if="value_for('fqdn')">
         ${display_field_for("shared")}
        </span>
       </td>
       <th class="list">
        ${label_for('user')}
       </th>
       <td class="list">
        ${user_email_link}
        <a py:if="user_change_text" href="${tg.url(user_change)}?id=${id}">
         <span py:content="user_change_text"/>
        </a>
        <a py:if="running_job" href="${tg.url(running_job)}">
          (Current Job)
        </a>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('private')}
       </th>
       <td class="list">
        ${display_field_for("private")}
       </td>
       <th class="list">
        ${label_for('loaned')}
       </th>
       <td class="list">
        ${loaned_email_link}
        <span py:if="loan_type">
            ${loan_widget.display(loan_type, id)}
        </span>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('lab_controller_id')}
       </th>
       <td class="list">
        ${display_field_for("lab_controller_id")}
       </td>
       <th class="list">
        ${label_for('mac_address')}
       </th>
       <td class="list">
        ${display_field_for("mac_address")}
       </td>
      </tr> 
      <tr class="list">
       <th class="list">
        ${label_for('type')}
       </th>
       <td class="list">
        ${display_field_for("type")}
       </td>
       <th class="list" py:if="show_cc or not readonly">
        ${label_for('cc')}
       </th>
       <td class="list" py:if="show_cc or not readonly">
        ${'; '.join(value_for("cc") or [])}
        <a py:if="not readonly" href="${tg.url('/cc_change', system_id=id)}">(Change)</a>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('hypervisor_id')}
       </th>
       <td class="list">
        ${display_field_for("hypervisor_id")}
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
