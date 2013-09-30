<div xmlns:py="http://purl.org/kid/ns#">
<script type='text/javascript'>
jQuery(function () {
    rw = new ReserveWorkflow(jQuery("#${name}"),
            "${tg.url(get_distros_rpc)}",
            "${tg.url(get_distro_trees_rpc)}");
});
</script>
<div class="reserveworkflow" id="${name}">
    <p py:if="tg.config('beaker.reservation_policy_url')">
        Please ensure that you adhere to the
        <a href="${tg.config('beaker.reservation_policy_url')}">reservation
        policy for Beaker systems</a>.
    </p>

    <form action="" class="form-horizontal">
      <fieldset>
        <legend>Distro</legend>
        <div class="control-group">
          <label class="control-label" for="${field_for('osmajor').field_id}">${field_for('osmajor').label}</label>
          <div class="controls">
            ${display_field_for('osmajor')}
          </div>
        </div>
        <div class="control-group">
          <label class="control-label" for="${field_for('tag').field_id}">${field_for('tag').label}</label>
          <div class="controls">
            ${display_field_for('tag')}
          </div>
        </div>
        <div class="control-group">
          <label class="control-label" for="${field_for('distro').field_id}">${field_for('distro').label}</label>
          <div class="controls">
            ${display_field_for('distro')}
          </div>
        </div>
      </fieldset>
    </form>

    <form action="${tg.url(action)}" class="form-horizontal">
      <fieldset>
        <legend>Distro Tree</legend>
        <div class="control-group">
          <label class="control-label" for="${field_for('lab_controller_id').field_id}">${field_for('lab_controller_id').label}</label>
          <div class="controls">
            ${display_field_for('lab_controller_id')}
          </div>
        </div>
        <div class="control-group">
          <label class="control-label" for="${field_for('distro_tree_id').field_id}">${field_for('distro_tree_id').label}</label>
          <div class="controls">
            ${display_field_for('distro_tree_id')}
          </div>
        </div>
        <div class="form-actions">
            <button class="btn search" type="submit" name="system_id" value="search">
                Show systems
            </button>
            <button class="btn auto_pick" type="submit">
                Auto pick system
            </button>
        </div>
      </fieldset>
    </form>
</div>
</div>
