
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemSchedulerSettingsView = Backbone.View.extend({
    template: JST['system-scheduler-settings'],
    events: {
        'change select[name=status]': 'status_changed',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function () {
        this.request_in_progress = false;
        this.listenTo(this.model, 'request', this.sync_started);
        this.listenTo(this.model, 'sync', this.sync_complete);
        this.listenTo(this.model, 'error', this.sync_error);
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('textarea, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('select').selectpicker();
        this.update_status_reason_state();
    },
    update_status_reason_state: function () {
        var status = $('select[name=status]').val();
        var reason_allowed = (status == 'Broken' || status == 'Removed');
        $('textarea[name=status_reason]').prop('disabled', !reason_allowed);
    },
    update_button_state: function () {
        this.$('.form-actions button').prop('disabled',
                (this.request_in_progress));
    },
    status_changed: function () {
        this.update_status_reason_state();
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
        this.$el.append(alert_for_xhr(xhr));
    },
    submit: function (evt) {
        if (this.request_in_progress) return false;
        this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Saving&hellip;');
        var attributes = _.object(_.map(this.$('textarea, select').filter(':enabled'),
                function (elem) { return [elem.name, $(elem).val()]; }));
        this.model.save(attributes, {patch: true, wait: true});
        evt.preventDefault();
    },
    reset: function (evt) {
        if (this.request_in_progress) return false;
        var model = this.model;
        this.$('textarea, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('select').selectpicker('refresh');
        evt.preventDefault();
    },
});

})();
