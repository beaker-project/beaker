<form xmlns:py="http://purl.org/kid/ns#"
     name="${name}"
     action="${action}"
     method="${method}" width="100%">
  <span py:if="not lab_controller">
    This system is not associated to a lab controller
  </span>
  <span py:if="lab_controller">
    <span py:for="note in provisioning_notes" py:content="note"/>
    <!-- !Display the provisioning panel only if appropriate -->
    <span py:if="provisioning_panel_id">
      <script language="JavaScript" type="text/JavaScript">
        ${name}_0 = new Provision('${id.field_id}', '${prov_install.field_id}', '${ks_meta.field_id}','${koptions.field_id}','${koptions_post.field_id}','${tg.url('/get_installoptions')}');
        addLoadEvent(${name}_0.initialize);
      </script>
      <div class="row-fluid" py:attrs="id=provisioning_panel_id">
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
          <span id="direct-provisioning-settings" py:if="reserved">
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
          <span id="scheduled-provisioning-settings" py:if="not reserved">
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
        <button type="submit" class="btn btn-primary" py:content="provisioning_button_label"/>
      </div>
      ${display_field_for("id")}
    </span>
  </span>
</form>
