<form xmlns:py="http://purl.org/kid/ns#"
     name="${name}"
     action="${action}"
     method="${method}" width="100%">
  <span py:if="not lab_controller">
    This system is not associated to a lab controller
  </span>
  <span py:if="lab_controller">
    <span py:if="automated and not can_reserve">
      You do not have access to schedule a job on this system.
    </span>
    <span py:if="not automated and not reserved and can_reserve">
      You can only provision if you have reserved the system.
    </span>
    <span py:if="not automated and not reserved and not can_reserve">
      You do not have access to reserve this system.
    </span>
    <span py:if="(automated and can_reserve) or (not automated and reserved)">
      <script language="JavaScript" type="text/JavaScript">
        ${name}_0 = new Provision('${id.field_id}', '${prov_install.field_id}', '${ks_meta.field_id}','${koptions.field_id}','${koptions_post.field_id}','${tg.url('/get_installoptions')}');
        addLoadEvent(${name}_0.initialize);
      </script>
      <div class="row-fluid">
        <div class="span4">
          ${display_field_for("prov_install")}
        </div>
        <div class="span8 form-horizontal">
          <div class="control-group">
            <label class="control-label"
                for="${ks_meta.field_id}"
                py:content="ks_meta.label"/>
            <div class="controls">
              ${display_field_for("ks_meta")}
            </div>
          </div>
          <div class="control-group">
            <label class="control-label"
                for="${koptions.field_id}"
                py:content="koptions.label"/>
            <div class="controls">
              ${display_field_for("koptions")}
            </div>
          </div>
          <div class="control-group">
            <label class="control-label"
                for="${koptions_post.field_id}"
                py:content="koptions_post.label"/>
            <div class="controls">
              ${display_field_for("koptions_post")}
            </div>
          </div>
          <span py:if="not automated">
            <div class="control-group" py:if="power_enabled">
              <div class="controls">
                <label class="checkbox">
                  ${display_field_for("reboot")}
                  ${reboot.label}
                </label>
              </div>
            </div>
            <div py:if="not power_enabled">
              This system is not configured for reboot support
            </div>
          </span>
          <span py:if="automated">
            <div class="control-group">
              <label class="control-label"
                for="${schedule_reserve_days.field_id}"
                py:content="schedule_reserve_days.label"/>
              <div class="controls">
                ${schedule_reserve_days.display()}
              </div>
            </div>
          </span>
        </div>
      </div>
      <div class="form-actions">
        <button type="submit" class="btn btn-primary" py:if="not automated">Provision</button>
        <button type="submit" class="btn btn-primary" py:if="automated">Schedule provision</button>
      </div>
      ${display_field_for("id")}
    </span>
  </span>
</form>
