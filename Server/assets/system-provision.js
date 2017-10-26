
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemProvisionView = Backbone.View.extend({
    template: JST['system-provision'],
    events: {
        'submit form': 'submit',
    },
    initialize: function (options) {
        this.listenTo(this.model,
                'change:lab_controller_id change:arches change:status change:can_configure_netboot change:possible_osmajors',
                this.render);
        this.request_in_progress = false;
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.distro_picker = new DistroPicker(_.extend({el: this.$('.distro-picker'), multiple: false,
          system: this.model.get('fqdn'), possible_osmajors: this.model.get('possible_osmajors')}, distro_picker_options));
        this.listenTo(this.distro_picker.selection, 'change', this.update_button_state);
        this.distro_picker.render();
        this.update_button_state();
    },
    update_button_state: function () {
        var distro_tree_selected = !!this.distro_picker.selection.get('distro_tree_id');
        this.$('.form-actions button').prop('disabled',
                (this.request_in_progress || !distro_tree_selected));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.request_in_progress = true;
        this.$('.submit-status').html('<i class="fa fa-spinner fa-spin"></i> ' +
                'Provisioning&hellip;');
        this.update_button_state();
        var msg = '<p>Are you sure you want to provision the system?</p>';
        if (this.model.get('current_reservation') &&
                this.model.get('current_reservation').get('user').get('user_name')
                != window.beaker_current_user.get('user_name')) {
            msg += ('<p><strong>You are not the current user of the system. '
                   + 'This action may interfere with another user.</strong></p>');
        }
        bootbox.confirm_as_promise(msg)
            .fail(_.bind(this.submit_cancelled, this))
            .done(_.bind(this.submit_confirmed, this));
    },
    submit_cancelled: function () {
        this.$('.submit-status').empty();
        this.request_in_progress = false;
        this.update_button_state();
    },
    submit_confirmed: function () {
        this.model.provision({
            distro_tree_id: this.distro_picker.selection.get('distro_tree_id'),
            ks_meta: this.$('[name=ks_meta]').val(),
            koptions: this.$('[name=koptions]').val(),
            koptions_post: this.$('[name=koptions_post]').val(),
            reboot: this.$('[name=reboot]:checked').val(),
            success: _.bind(this.submit_success, this),
            error: _.bind(this.submit_error, this),
        });
    },
    submit_success: function () {
        this.$('.submit-status').empty();
        this.request_in_progress = false;
        this.update_button_state();
        $.bootstrapGrowl('<h4>Provisioning successful</h4> Provisioning commands ' +
                'have been enqueued and will be executed by the lab controller shortly.',
                {type: 'success'});
        //refresh power commands grid
        this.model.command_queue.fetch();
    },
    submit_error: function (model, xhr) {
        this.$('.submit-status').empty();
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.form-actions').prepend(alert_for_xhr(xhr, 'Failed to provision'));
    },
});

})();
