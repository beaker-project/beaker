;(function () {

var DistroPickerSelection = Backbone.Model.extend({
});

window.DistroPicker = Backbone.View.extend({
    tagName: 'fieldset',
    template: JST['distro-picker'],
    events: {
        'change select': 'update_state',
        'change select.distro_filter_criterion': 'get_distros',
        'change select.distro_tree_filter_criterion': 'get_distro_trees',
    },
    initialize: function (options) {
        _.defaults(options, {options: {}, selection: {}});
        this.osmajors = options.options['osmajor'];
        this.tags = options.options['tag'];
        this.distros = options.options['distro'];
        this.distro_trees = options.options['distro_tree_id'];
        this.selection = new DistroPickerSelection({
            osmajor: options.selection['osmajor'],
            tag: options.selection['tag'],
            distro: options.selection['distro'],
            distro_tree_id: options.selection['distro_tree_id'],
        });
    },
    render: function () {
        this.$el.html(this.template(this));
        this.update_state();
        return this;
    },
    update_state: function () {
        // enable or disable selects as appropriate
        var has_distros = this.$('select[name=distro] option').length > 0;
        this.$('select[name=distro]').prop('disabled', !has_distros);
        var has_distro_trees = this.$('select[name=distro_tree_id] option').length > 0;
        this.$('select[name=distro_tree_id]').prop('disabled',
                !has_distros || !has_distro_trees);
        // update the current selection state
        var selection = this.selection;
        this.$('select').each(function (i, elem) {
            selection.set(elem.name, $(elem).val());
        });
    },
    get_distros: function () {
        if (this.get_distros_xhr)
            this.get_distros_xhr.abort();
        if (this.$('select[name=osmajor]').val()) {
            var loading = $('<span><i class="icon-spinner icon-spin"></i> Loading&hellip;</span>');
            this.$('select[name=distro]').after(loading);
            var xhr = this.get_distros_xhr = $.ajax({
                url: beaker_url_prefix +
                        'reserveworkflow/get_distro_options?tg_format=json&' +
                        this.$('.distro_filter_criterion').serialize(),
                dataType: 'json',
            });
            xhr.done(_.bind(this.replace_distros, this));
            xhr.always(function () { loading.remove() });
        } else {
            // shortcut
            this.replace_distros({options: []});
        }
    },
    replace_distros: function (result) {
        var select = this.$('select[name=distro]');
        select.empty();
        _.each(result.options, function (option) {
            select.append($('<option/>').attr('value', option).text(option));
        });
        select.change();
    },
    get_distro_trees: function () {
        if (this.get_distro_trees_xhr)
            this.get_distro_trees_xhr.abort();
        if (this.$('select[name=distro]').val()) {
            var loading = $('<span><i class="icon-spinner icon-spin"></i> Loading&hellip;</span>');
            this.$('select[name=distro_tree_id]').after(loading);
            var xhr = this.get_distro_trees_xhr = $.ajax({
                url: beaker_url_prefix +
                        'reserveworkflow/get_distro_tree_options?tg_format=json&' +
                        this.$('.distro_tree_filter_criterion').serialize(),
                dataType: 'json',
            });
            xhr.done(_.bind(this.replace_distro_trees, this));
            xhr.always(function () { loading.remove() ; });
        } else {
            // shortcut
            this.replace_distro_trees({options: []});
        }
    },
    replace_distro_trees: function (result) {
        var select = this.$('select[name=distro_tree_id]');
        select.empty();
        _.each(result.options, function (option) {
            select.append($('<option/>').attr('value', option[0]).text(option[1]));
        });
        select.change();
    },
});

})();
