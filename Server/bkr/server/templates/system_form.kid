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

    // Get The element that contains our condition text
    var condition_elem = $('label[for="form_status"]').parent().next()
    var condition_text = $.trim($(condition_elem).text())
    // Hide the condition field if we are in view mode
    if (condition_text == 'Manual' || condition_text == 'Automated') {
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
  action="${action}"
  method="${method}" width="100%">

    <div xmlns:py="http://purl.org/kid/ns#">
     <span py:if="options.get('edit')" py:strip="1">
      ${display_system_property("id")}
     </span>
     <table class="list" style="margin-bottom:1em">
      <tr class="list">
       <th class="list">
        ${label_for('fqdn')}
       </th>
       <td class="list" colspan="3">
        ${display_system_property("fqdn")}
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
        ${display_system_property("vendor")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('lender')}
       </th>
       <td class="list">
        ${display_system_property('lender')}
       </td>
       <th class="list">
        ${label_for('model')}
       </th>
       <td class="list">
        ${display_system_property("model")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('serial')}
       </th>
       <td class="list">
        ${display_system_property("serial")}
       </td>
       <th class="list">
        ${label_for('location')}
       </th>
       <td class="list">
        ${display_system_property("location")}
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('status')}
       </th>
       <td class="list">
        ${display_system_property("status")}
       </td>
       <th class="list">
        ${label_for('owner')}
       </th>
       <td class="list">
        ${owner_email_link}
        <a py:if="owner_change_text" href="${tg.url(owner_change)}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
        <span py:if="not tg.identity.anonymous and system_actions is not None" py:strip="1">
            ${system_actions.display(loan_options=options['loan'], report_problem_options=options['report_problem'])}
        </span>
       </td>
      </tr>
      <tr class="list" id="condition_report_row">
       <th class="list" >
        ${label_for('status_reason')}
       </th>
       <td class="list"> 
        ${display_system_property("status_reason")}
       </td>
      </tr>
      <tr class="list"> 
       <th class="list">
        ${label_for('shared')}
       </th>
       <td class="list">
        <span py:if="value_for('fqdn')">
         ${display_system_property("shared")}
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
        ${display_system_property("private")}
       </td>
       <th class="list">
        ${label_for('loaned')}
       </th>
       <td class="list" py:if='value'>
        <span id='loanee-name'>${value.get('loaned')}</span>
        <span py:strip="1" py:if="show_loan_options">
         ${loan_widget.display(value, comment=loan_comment)}
        </span>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('lab_controller_id')}
       </th>
       <td class="list">
        ${display_system_property("lab_controller_id")}
       </td>
       <th class="list">
        ${label_for('mac_address')}
       </th>
       <td class="list">
        ${display_system_property("mac_address")}
       </td>
      </tr> 
      <tr class="list">
       <th class="list">
        ${label_for('type')}
       </th>
       <td class="list">
        ${display_system_property("type")}
       </td>
       <th class="list">
        ${label_for('cc')}
       </th>
       <td class="list">
        ${'; '.join(value_for("cc") or [])}
        <a href="${tg.url('/cc_change', system_id=id)}">(Change)</a>
       </td>
      </tr>
      <tr class="list">
       <th class="list">
        ${label_for('hypervisor_id')}
       </th>
       <td class="list">
        ${display_system_property("hypervisor_id")}
       </td>
       <th class="list">
        ${label_for('kernel_type_id')}
       </th>
       <td class="list">
        ${display_system_property("kernel_type_id")}
       </td>
      </tr>
     </table>
        <span py:if='options.get("edit")' py:strip='1'>
         <a class="button" href="javascript:document.${name}.submit();">Save Changes</a>
        </span>
        <span py:if='not options.get("edit")' py:strip='1'>
         <a class="button" href="${tg.url('/edit/%s' % value_for('fqdn'))}">Edit System</a>
        </span>
    </div>
</form>
</div>
