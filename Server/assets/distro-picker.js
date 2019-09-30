
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

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
        'change select.unsupported_lab_controllers_filter_criterion': 'get_unsupported_lab_controllers',
    },
    initialize: function (options) {
        _.defaults(options, {multiple: true, selection: {}});
        this.multiple = options.multiple;
        this.system = options.system; // only show distros compatible with this system
        this.osmajors = options.possible_osmajors ? options.possible_osmajors : options.osmajor;
        this.tags = options.tag;
        this.distros = options.distro;
        this.distro_trees = options.distro_tree_id;
        this.selection = new DistroPickerSelection({
            osmajor: options.selection.osmajor,
            tag: options.selection.tag,
            distro: options.selection.distro,
            distro_tree_id: options.selection.distro_tree_id,
            distro_tree_label: '',
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
            // XXX this distro_tree_label stuff is a bit of a hack, we should 
            // keep an actual DistroTree object instead of just re-using the 
            // label that the server gives us
            if (elem.name == 'distro_tree_id') {
                selection.set('distro_tree_label', $(elem).children('option:checked').text());
            }
        });
    },
    get_distros: function () {
        if (this.get_distros_xhr)
            this.get_distros_xhr.abort();
        if (this.$('select[name=osmajor]').val()) {
            var loading = $('<span><i class="fa fa-spinner fa-spin"></i> Loading&hellip;</span>');
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
            var loading = $('<span><i class="fa fa-spinner fa-spin"></i> Loading&hellip;</span>');
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
    get_unsupported_lab_controllers: function () {
        if (this.get_unsupported_lab_controllers_xhr)
            this.get_unsupported_lab_controllers_xhr.abort();
        if (this.$('select[name=distro_tree_id]').val()) {
            var loading = $('<span><i class="fa fa-spinner fa-spin"></i> Loading&hellip;</span>');
            this.$('div.lab-controller-warning').after(loading);
            var xhr = this.get_unsupported_lab_controllers_xhr = $.ajax({
                url: beaker_url_prefix +
                        'reserveworkflow/unsupported-lab-controllers?' +
                        this.$('.unsupported_lab_controllers_filter_criterion').serialize(),
                dataType: 'json',
            });
            xhr.done(_.bind(this.replace_unsupported_lab_controllers, this));
            xhr.always(function () { loading.remove() ; });
        } else {
            // shortcut
            this.replace_unsupported_lab_controllers({options: []});
        }
    },
    replace_unsupported_lab_controllers: function (result) {
        var warningDiv = this.$('div.lab-controller-warning');
        warningDiv.empty();
        for(var option in result.options){
            var options = result.options[option]
            if(options.length){
                warningDiv.append($('<strong>').text("The distro tree you have selected (" + option + ") is not available in the following lab controllers:"));
                for(var labControllerFQDN in options){
                    warningDiv.append($('<p>').text(options[labControllerFQDN]));
                }
            }
        }
    },
});

window.DistroPickerModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['distro-picker-modal'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function (options) {
        this.distro_picker = new DistroPicker({
            multiple: false,
            system: options.system,
            osmajor: options.osmajor,
            tag: options.tag,
            distro: options.distro,
            distro_tree_id: options.distro_tree_id,
            selection: options.selection,
        });
        this.selection = this.distro_picker.selection;
        this.render();
        this.$el.modal();
        this.$('[name=osmajor]').focus();
    },
    render: function () {
        this.$el.html(this.template({}));
        this.distro_picker.setElement(this.$('.distro-picker')).render();
    },
    submit: function (evt) {
        evt.preventDefault();
        this.trigger('select', this.selection);
        this.$el.modal('hide');
    },
});

})();
