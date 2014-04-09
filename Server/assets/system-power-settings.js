
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPowerSettingsView = Backbone.View.extend({
    template: JST['system-power-settings'],
    events: {
        'click #reprovision_distro_tree button': 'pick_reprovision_distro_tree',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function (options) {
        this.distro_picker_options = options.distro_picker_options;
        this.request_in_progress = false;
        this.listenTo(this.model, 'request', this.sync_started);
        this.listenTo(this.model, 'sync', this.sync_complete);
        this.listenTo(this.model, 'error', this.sync_error);
        this.listenTo(this.model, 'change:can_change_power change:lab_controller_id', this.render);
        this.render();
    },
    render: function () {
        if (!window.beaker_current_user) {
            this.$el.html('<div class="alert alert-info">You are not logged in.</div>');
            return;
        } else if (!this.model.get('can_change_power')) {
            this.$el.html('<div class="alert alert-info">You do not have permission ' +
                    'to edit power configuration for this system.</div>');
            return;
        } else if (!this.model.get('lab_controller_id')) {
            this.$el.html('<div class="alert alert-info">System is not attached ' +
                    'to a lab controller.</div>');
            return;
        }
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            if (elem.name != 'reprovision_distro_tree_id')
                $(elem).val([model.get(elem.name)]);
        });
        if (model.get('reprovision_distro_tree')) {
            var dt = model.get('reprovision_distro_tree');
            this.$('[name=reprovision_distro_tree_id]').val(dt.get('id'));
            this.$('#reprovision_distro_tree span').text(
                    dt.get('distro').get('name') + ' ' + dt.get('variant') +
                    ' ' + dt.get('arch'));
        }
        this.$('select').selectpicker();
    },
    pick_reprovision_distro_tree: function () {
        var picker = new DistroPickerModal({
            system: this.model.get('fqdn'),
            options: this.distro_picker_options,
        });
        var view = this;
        this.listenToOnce(picker, 'select', function (selection) {
            view.$('[name=reprovision_distro_tree_id]').val(selection.get('distro_tree_id'));
            view.$('#reprovision_distro_tree span').text(selection.get('distro_tree_label'));
        });
    },
    update_button_state: function () {
        this.$('.form-actions button').prop('disabled',
                (this.request_in_progress));
    },
    sync_started: function () {
        this.request_in_progress = true;
        this.update_button_state();
    },
    sync_complete: function () {
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.sync-status').empty();
    },
    sync_error: function (model, xhr) {
        this.request_in_progress = false;
        this.update_button_state();
        this.$('.sync-status').empty();
        this.$el.append(
            $('<div class="alert alert-error"/>')
            .text('Server request failed: ' + xhr.statusText + ': ' +
                    xhr.responseText));
    },
    submit: function (evt) {
        if (this.request_in_progress) return false;
        this.$('.sync-status').html('<i class="icon-spinner icon-spin"></i> Saving&hellip;');
        var form_values = this.$('form').serializeArray();
        var attributes = _.object(_.pluck(form_values, 'name'), _.pluck(form_values, 'value'));
        // reprovision_distro_tree needs special treatment
        rpdtid = attributes['reprovision_distro_tree_id'];
        delete attributes['reprovision_distro_tree_id'];
        if (rpdtid)
            attributes['reprovision_distro_tree'] = {'id': rpdtid};
        else
            attributes['reprovision_distro_tree'] = null;
        this.model.save(attributes, {patch: true, wait: true});
        evt.preventDefault();
    },
    reset: function (evt) {
        if (this.request_in_progress) return false;
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            if (elem.name != 'reprovision_distro_tree_id')
                $(elem).val([model.get(elem.name)]);
        });
        if (model.get('reprovision_distro_tree')) {
            var dt = model.get('reprovision_distro_tree');
            this.$('[name=reprovision_distro_tree_id]').val(dt.get('id'));
            this.$('#reprovision_distro_tree span').text(
                    dt.get('distro').get('name') + ' ' + dt.get('variant') +
                    ' ' + dt.get('arch'));
        }
        this.$('select').selectpicker('refresh');
        evt.preventDefault();
    },
});

})();
