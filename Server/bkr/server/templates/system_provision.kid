<form xmlns:py="http://purl.org/kid/ns#"
     name="${name}"
     action="${action}"
     method="${method}" width="100%">
  <span py:if="not lab_controller">
    This system is not associated to a lab controller
  </span>
  <span py:if="lab_controller">
    <span py:if="reserved and not can_reserve">
      After returning this system, you will no longer be able to provision it.
    </span>
    <span py:if="not reserved and not can_reserve">
      You do not have access to provision this system.
    </span>
    <span py:if="not automated and reserved">
      System will be provisioned directly.
    </span>
    <span py:if="not automated and not reserved and can_reserve">
      Reserve this system to provision it.
    </span>
    <!-- !Automated provisioning may be direct or through the scheduler
          We avoid the word "immediate", as it is misleading when the system
          has no automatic power control configured (the netboot files are
          written immediately, but you have to reboot the system to trigger
          reprovisioning).
          We avoid "on next reboot", as it is misleading when automatic power
          control *is* configured (since Beaker will reboot the system
          automatically).
          We avoid the word "manually" as it suggests there may be more to do
          after clicking the "Provision" button (which is only the case if
          power control is not configured).
    -->
    <span py:if="automated and not borrowed and can_reserve">
      Provisioning will use a scheduled job. Borrow and reserve this system to provision it directly instead.
    </span>
    <span py:if="automated and borrowed and not reserved and can_reserve">
      Provisioning will use a scheduled job. Reserve this system to provision it directly instead.
    </span>
    <span py:if="automated and borrowed and reserved and can_reserve">
      System will be provisioned directly. Return this system to use a scheduled job instead.
    </span>
    <!-- !Display the provisioning panel only if appropriate -->
    <span py:if="reserved or (automated and can_reserve)">
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
        <!-- !Provision immediately if we already have a manual reservation -->
        <button type="submit" class="btn btn-primary" py:if="reserved">Provision</button>
        <!-- !Otherwise provisioning must go through the scheduler -->
        <button type="submit" class="btn btn-primary" py:if="not reserved">Schedule provision</button>
      </div>
      ${display_field_for("id")}
    </span>
  </span>
</form>
