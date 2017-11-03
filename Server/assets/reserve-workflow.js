
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var ReserveWorkflowSelection = Backbone.Model.extend({
});

window.ReserveWorkflow = Backbone.View.extend({
    template: JST['reserve-workflow'],
    events: {
        'submit form': 'submit',
        'change .system-picker input, select': 'update_selection',
        'change .job-options input': 'update_selection',
    },
    initialize: function (options) {
        this.request_in_progress = false;
        this.distro_picker = new DistroPicker({
            osmajor: options.options.osmajor,
            tag: options.options.tag,
            distro: options.options.distro,
            distro_tree_id: options.options.distro_tree_id,
            selection: options.selection,
        });
        this.labs = options.options['lab'];
        var default_pick = (options.selection['system'] ? 'fqdn' : 'auto');
        this.selection = new ReserveWorkflowSelection({
            lab: options.selection['lab'] || this.labs[0],
            system: options.selection['system'],
            pick: options.selection['pick'] || default_pick,
            reserve_duration: options.selection['reserve_duration'] || (24 * 60 * 60),
        });
        this.reserve_input = new ReservationDurationSelection(
            {reserve_duration: this.selection.get('reserve_duration')});
        // sync our selection from distro picker's selection
        this.listenTo(this.distro_picker.selection, 'change', function (model) {
            this.selection.set('distro_tree_id', model.get('distro_tree_id'));
        });
        this.listenTo(this.distro_picker.selection, 'change', this.update_query_string);
        this.listenTo(this.selection, 'change', this.update_button_state);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this));
        this.$('.job-options > legend').after(this.reserve_input.$el);
        this.reserve_input.render();
        this.distro_picker.setElement(this.$('.distro-picker')).render();
        this.update_button_state();
    },
    update_query_string: function () {
        // Use window.replaceState to add query parameters for distro tree 
        // selection, so that if the user comes back to this page the 
        // distro_tree_id <select/> will be populated without needing to wait for 
        // an AJAX request.
        var qs = new URI(window.location.search);
        if (this.distro_picker.selection.get('osmajor'))
            qs.setSearch('osmajor', this.distro_picker.selection.get('osmajor'));
        if (this.distro_picker.selection.get('tag'))
            qs.setSearch('tag', this.distro_picker.selection.get('tag'));
        if (this.distro_picker.selection.get('distro'))
            qs.setSearch('distro', this.distro_picker.selection.get('distro'));
        window.history.replaceState(undefined, undefined, qs.toString());
    },
    update_button_state: function () {
        var distro_tree_selected = ((this.selection.get('distro_tree_id') || []).length > 0);
        // enable/disable submit button
        this.$('.form-actions button').prop('disabled',
                (this.request_in_progress || !distro_tree_selected));
        // update href for system picker
        var href = new URI('../reserve_system');
        if (distro_tree_selected)
            href.setSearch('distro_tree_id', this.selection.get('distro_tree_id')[0]);
        this.$('a.select-system').attr('href', href.toString());
    },
    update_selection: function (evt) {
        var elem = evt.currentTarget;
        this.selection.set(elem.name, $(elem).val());
    },
    submit: function (evt) {
        evt.preventDefault();
        this.selection.set('reserve_duration', this.reserve_input.get_reservation_duration().asSeconds());
        var xhr = $.ajax({
            url: 'doit',
            type: 'POST',
            data: this.selection.attributes,
            traditional: true,
        });
        this.request_in_progress = true;
        this.$('.submit-status').html('<i class="fa fa-spinner fa-spin"></i> Submitting&hellip;');
        this.update_button_state();
        this.$('.form-actions .alert-error').remove();
        xhr.done(function (result) {
            // don't re-enable the button in the success case, we want the user 
            // to wait for their browser to load the job page
            window.location = xhr.getResponseHeader('Location');
        });
        xhr.fail(_.bind(function () {
            this.request_in_progress = false;
            this.$('.submit-status').empty();
            this.update_button_state();
            this.$('.form-actions').prepend(alert_for_xhr(xhr, 'Failed to submit job'));
        }, this));
    },
});

})();
