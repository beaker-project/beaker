<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
$(document).ready(function(){ 
    $("#form_status").change(function() {
        if ($('#form_status :selected').text() == 'Broken' || $('#form_status :selected').text() == 'Removed') {
             $('#condition_report_row').show();
        };
        if ($('#form_status :selected').text() == 'Manual' || $('#form_status :selected').text() == 'Automated') {
             $('#condition_report_row').hide();
        } 
    });

    if ($('#form_status :selected').text() == 'Manual' || $('#form_status :selected').text() == 'Automated') {
         $('#condition_report_row').hide();
    } 

    // Get The element that contains our condition text
    var condition_elem = $('label[for="form_status"]').next();
    var condition_text = $.trim($(condition_elem).text())
    // Hide the condition field if we are in view mode
    if (condition_text == 'Manual' || condition_text == 'Automated') {
        $('#condition_report_row').hide();
    }
});
</script>
<style type="text/css">
.uneditable-input {
    /* Bootstrap sets cursor: not-allowed; which is a bit irritating for us here */
    cursor: auto !important;
}
</style>
<label py:def="label_for(field_name)"
       class="control-label"
       for="${field_for(field_name).field_id}"
       title="${getattr(field_for(field_name), 'help_text', '')}">
    ${field_for(field_name).label}
</label>
<form xmlns:py="http://purl.org/kid/ns#"
  name="${name}"
  action="${action}"
  method="${method}"
  class="form-horizontal">

     <span py:if="options.get('edit')" py:strip="1">
      ${display_system_property("id")}
     </span>

  <div py:if="options.get('edit')" class="row-fluid">
    <div class="span12">
      <div class="control-group ${error_for('fqdn') and 'error' or ''}">
        ${label_for('fqdn')}
        <div class="controls">
        ${display_system_property("fqdn")}
        <span py:if="error_for('fqdn')" class="help-inline" py:content="error_for('fqdn')" />
        </div>
      </div>
    </div>
  </div>

  <div class="row-fluid">
    <div class="span6">
      <div class="control-group">
        ${label_for('date_added')}
        <div class="controls text-controls">
        <span class="datetime">${value_for("date_added")}</span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('date_lastcheckin')}
        <div class="controls text-controls">
        <span class="datetime">${value_for("date_lastcheckin")}</span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('lender')}
        <div class="controls">
        ${display_system_property('lender')}
        </div>
      </div>
      <div class="control-group">
        ${label_for('serial')}
        <div class="controls">
        ${display_system_property("serial")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('status')}
        <div class="controls">
        ${display_system_property("status")}
        </div>
      </div>
      <div class="control-group" id="condition_report_row">
        ${label_for('status_reason')}
        <div class="controls">
        ${display_system_property("status_reason")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('shared')}
        <div class="controls">
        <span py:if="value_for('fqdn')">
         ${display_system_property("shared")}
        </span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('private')}
        <div class="controls">
        ${display_system_property("private")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('lab_controller_id')}
        <div class="controls">
        ${display_system_property("lab_controller_id")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('type')}
        <div class="controls">
        ${display_system_property("type")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('hypervisor_id')}
        <div class="controls">
        ${display_system_property("hypervisor_id")}
        </div>
      </div>
    </div>

    <div class="span6">
      <div class="control-group">
        ${label_for('date_modified')}
        <div class="controls text-controls">
        <span class="datetime">${value_for("date_modified")}</span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('vendor')}
        <div class="controls">
        ${display_system_property("vendor")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('model')}
        <div class="controls">
        ${display_system_property("model")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('location')}
        <div class="controls">
        ${display_system_property("location")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('owner')}
        <div class="controls">
        ${owner_email_link}
        <a py:if="owner_change_text" class="btn" href="${tg.url(owner_change)}?id=${id}">
         <span py:content="owner_change_text"/>
        </a>
        <span py:if="not tg.identity.anonymous and system_actions is not None" py:strip="1">
            ${system_actions.display(loan_options=options['loan'], report_problem_options=options['report_problem'])}
        </span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('user')}
        <div class="controls">
        ${user_email_link}
        <a py:if="user_change_text" class="btn" href="${tg.url(user_change)}?id=${id}">
         <span py:content="user_change_text"/>
        </a>
        <a py:if="running_job" href="${tg.url(running_job)}">
          (Current Job)
        </a>
        </div>
      </div>
      <div class="control-group">
        ${label_for('loaned')}
        <div class="controls" py:if="value">
        <span id='loanee-name'>${value.get('loaned')}</span>
        <span py:strip="1" py:if="show_loan_options">
         ${loan_widget.display(value, comment=loan_comment)}
        </span>
        </div>
      </div>
      <div class="control-group">
        ${label_for('mac_address')}
        <div class="controls">
        ${display_system_property("mac_address")}
        </div>
      </div>
      <div class="control-group">
        ${label_for('cc')}
        <div class="controls">
        ${'; '.join(value_for("cc") or [])}
        <a class="btn" href="${tg.url('/cc_change', system_id=id)}">Change</a>
        </div>
      </div>
      <div class="control-group">
        ${label_for('kernel_type_id')}
        <div class="controls">
        ${display_system_property("kernel_type_id")}
        </div>
      </div>
    </div>
  </div>

      <div class="form-actions" py:if="options.get('edit')">
         <a class="btn btn-primary" href="javascript:document.${name}.submit();">Save Changes</a>
      </div>
        <span py:if='not options.get("edit")' py:strip='1'>
         <a class="btn" href="${tg.url('/edit/%s' % value_for('fqdn'))}">Edit System</a>
        </span>
</form>
</div>
