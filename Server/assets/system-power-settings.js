
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPowerSettingsView = Backbone.View.extend({
    template: JST['system-power-settings'],
    events: {
        'click #reprovision_distro_tree button': 'pick_reprovision_distro_tree',
        'click #show_password button': 'showPassword',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function (options) {
        this.distro_picker_options = options.distro_picker_options;
        this.listenTo(this.model, 'change:can_change_power change:lab_controller_id', this.render);
        this.render();
    },
    render: function () {
        if (!window.beaker_current_user) {
            this.$el.html('<div class="alert alert-info">You are not logged in.</div>');
            return;
        } else if (!this.model.get('can_view_power')) {
            this.$el.html('<div class="alert alert-info">You do not have permission ' +
                    'to view power configuration for this system.</div>');
            return;
        } else if (!this.model.get('lab_controller_id')) {
            this.$el.html('<div class="alert alert-info">System is not attached ' +
                    'to a lab controller.</div>');
            return;
        }
        var readonly = !this.model.get('can_change_power');
        this.$el.html(this.template(
                _.extend({readonly: readonly}, this.model.attributes)));
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            if (elem.name != 'reprovision_distro_tree_id')
                $(elem).val([model.get(elem.name)]);
            if (readonly)
                $(elem).prop('disabled', true);
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
        var picker = new DistroPickerModal(_.extend({system: this.model.get('fqdn')},
                        this.distro_picker_options));
        var view = this;
        this.listenToOnce(picker, 'select', function (selection) {
            view.$('[name=reprovision_distro_tree_id]').val(selection.get('distro_tree_id'));
            view.$('#reprovision_distro_tree span').text(selection.get('distro_tree_label'));
        });
    },
    showPassword: function (evt) {
        evt.preventDefault()
        this.$("#show_password i").toggleClass('fa-eye').toggleClass('fa-eye-slash')

        this.$("#show_password input").attr("type") === "password"
            ? this.$("#show_password input").attr('type', 'text')
            : this.$("#show_password input").attr('type', 'password')
    },
    sync_success: function (response, status, xhr) {
        this.$('.form-actions button').button('reset');
    },
    sync_error: function (xhr) {
        this.$('.form-actions button').button('reset');
        this.$('.sync-status').append(alert_for_xhr(xhr));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.form-actions button').button('loading');
        var form_values = this.$('form').serializeArray();
        var attributes = _.object(_.pluck(form_values, 'name'), _.pluck(form_values, 'value'));
        // reprovision_distro_tree needs special treatment
        rpdtid = attributes['reprovision_distro_tree_id'];
        delete attributes['reprovision_distro_tree_id'];
        if (rpdtid)
            attributes['reprovision_distro_tree'] = {'id': rpdtid};
        else
            attributes['reprovision_distro_tree'] = null;
        this.model.save(attributes, {patch: true, wait: true})
            .done(_.bind(this.sync_success, this))
            .fail(_.bind(this.sync_error, this));
    },
    reset: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
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
    },
});

})();
