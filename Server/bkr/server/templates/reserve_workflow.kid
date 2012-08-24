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

    <form action="">
        <h3>Distro</h3>
        <div>
            <label for="${field_for('osmajor').field_id}">${field_for('osmajor').label}</label>
            ${display_field_for('osmajor')}
        </div>
        <div>
            <label for="${field_for('tag').field_id}">${field_for('tag').label}</label>
            ${display_field_for('tag')}
        </div>
        <div>
            <label for="${field_for('distro').field_id}">${field_for('distro').label}</label>
            ${display_field_for('distro')}
        </div>
    </form>

    <form action="${tg.url(action)}">
        <h3>Distro Tree</h3>
        <div>
            <label for="${field_for('lab_controller_id').field_id}">${field_for('lab_controller_id').label}</label>
            ${display_field_for('lab_controller_id')}
        </div>
        <div>
            ${display_field_for('distro_tree_id')}
        </div>
        <div>
            <button class="search" type="submit" name="system_id" value="search">
                Show systems
            </button>
            <button class="auto_pick" type="submit">
                Auto pick system
            </button>
        </div>
    </form>
</div>
</div>
