ReserveWorkflow = function (div, get_distros_rpc, get_distro_trees_rpc) {
    bindMethods(this);
    this.div = div;
    this.get_distros_rpc = get_distros_rpc;
    this.get_distro_trees_rpc = get_distro_trees_rpc;
    this.deferred_get_distros = new Deferred();
    this.deferred_get_distro_trees = new Deferred();
    $('select', this.div).change(this.update_state);
    $('.distro_filter_criterion', this.div).change(this.get_distros);
    $('.distro_tree_filter_criterion', this.div).change(this.get_distro_trees);
    this.update_state();
};

ReserveWorkflow.prototype.get_distros = function() {
    this.deferred_get_distros.cancel();
    if ($('select[name=osmajor]', this.div).val()) {
        var loader = new AjaxLoader2($('select[name=distro]', this.div));
        var d = this.deferred_get_distros = loadJSONDoc(
                this.get_distros_rpc + '?tg_format=json&' +
                $('.distro_filter_criterion', this.div).serialize());
        d.addCallback(this.replaceDistros);
        d.addBoth(loader.remove);
    } else {
        // shortcut
        this.replaceDistros({options: []});
    }
};

ReserveWorkflow.prototype.replaceDistros = function(result) {  
    var select = $('select[name=distro]', this.div);
    select.empty();
    $.each(result.options, function (i, option) {
        select.append($('<option/>').attr('value', option).text(option));
    });
    select.change();
}

ReserveWorkflow.prototype.get_distro_trees = function () {
    this.deferred_get_distro_trees.cancel();
    if ($('select[name=distro]', this.div).val()) {
        var loader = new AjaxLoader2($('select[name=distro_tree_id]', this.div));
        var d = this.deferred_get_distro_trees = loadJSONDoc(
                this.get_distro_trees_rpc + '?tg_format=json&' +
                $('.distro_tree_filter_criterion', this.div).serialize());
        d.addCallback(this.replace_distro_trees);
        d.addBoth(loader.remove);
    } else {
        // shortcut
        this.replace_distro_trees({options: []});
    }
};

ReserveWorkflow.prototype.replace_distro_trees = function (result) {
    var select = $('select[name=distro_tree_id]', this.div);
    select.empty();
    $.each(result.options, function (i, option) {
        select.append($('<option/>').attr('value', option[0]).text(option[1]));
    });
    select.change();
};

var enable_if = function (s, enable) {
    if (enable)
        s.removeAttr('disabled');
    else
        s.attr('disabled', 'disabled');
};
ReserveWorkflow.prototype.update_state = function () {
    window.history.replaceState(undefined, undefined, '?' + $('form', this.div).serialize());

    var has_distros = $('select[name=distro] option', this.div).length > 0;
    var has_distro_trees = $('select[name=distro_tree_id] option', this.div).length > 0;
    var distro_tree_selected = $('select[name=distro_tree_id] option:selected', this.div).length > 0;
    var distro_tree_multi = $('select[name=distro_tree_id] option:selected', this.div).length > 1;
    enable_if($('select[name=distro]', this.div),
            has_distros);
    enable_if($('select[name=distro_tree_id]', this.div),
            has_distros && has_distro_trees);
    enable_if($('button.auto_pick', this.div),
            has_distros && has_distro_trees && distro_tree_selected);
    enable_if($('button.search', this.div),
            has_distros && has_distro_trees && distro_tree_selected && !distro_tree_multi);
};
