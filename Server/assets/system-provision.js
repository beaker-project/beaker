;(function () {

window.SystemProvisionView = Backbone.View.extend({
    template: JST['system-provision'],
    events: {
        'submit form': 'submit',
    },
    initialize: function (options) {
        this.request_in_progress = false;
        this.distro_picker = new DistroPicker({
            multiple: false,
            system: this.model.get('fqdn'),
            options: options.distro_picker_options,
        });
        this.listenTo(this.model,
                'change:lab_controller_id change:arches change:status change:can_power',
                this.render);
        this.listenTo(this.distro_picker.selection, 'change', this.update_button_state);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.distro_picker.setElement(this.$('.distro-picker')).render();
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
        this.$('.submit-status').html('<i class="icon-spinner icon-spin"></i> ' +
                'Provisioning&hellip;');
        this.update_button_state();
        bootbox.confirm_as_promise('Are you sure you want to provision the system?')
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
        this.$('.submit-status').text('Provisioning commands enqueued!');
        this.request_in_progress = false;
        this.update_button_state();
    },
    submit_error: function (model, xhr) {
        this.$('.submit-status').empty();
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.form-actions').prepend(
                $('<div class="alert alert-error"></div>')
                .text('Failed to provision: ' +
                    xhr.statusText + ': ' + xhr.responseText));
    },
});

})();
