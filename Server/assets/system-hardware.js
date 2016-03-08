
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemHardwareEssentialsView = Backbone.View.extend({
    template: JST['system-hardware-essentials'],
    events: {
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
        this.$('input, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('select').selectpicker();
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
        this.$el.append(alert_for_xhr(xhr));
    },
    submit: function (evt) {
        if (this.request_in_progress) return false;
        this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Saving&hellip;');
        var attributes = _.object(_.map(this.$('input, select'),
                function (elem) { return [elem.name, $(elem).val()]; }));
        this.model.save(attributes, {patch: true, wait: true});
        evt.preventDefault();
    },
    reset: function (evt) {
        if (this.request_in_progress) return false;
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('select').selectpicker('refresh');
        evt.preventDefault();
    },
});

window.SystemHardwareDetailsView = Backbone.View.extend({
    template: JST['system-hardware-details'],
    events: {
        'click .edit': 'edit',
        'click .scan': 'scan',
    },
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    edit: function () {
        new SystemHardwareDetailsEdit({model: this.model});
    },
    scan: function (evt) {
        this.$('.alert-error').remove();
        model = this.model
        $(evt.currentTarget).button('loading');
        $.ajax({
            url: beaker_url_prefix + 'jobs/+inventory',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'fqdn': model.get('fqdn')}),
            success: function (response, status, jqxhr) {
                model.set({'in_progress_scan': {'recipe_id': response['recipe_id'],
                                                'status': response['status']}});
                $(evt.currentTarget).button('reset');
            },
            error: function (xhr, status, error) {
                $('.hardware-scan-status').after(alert_for_xhr(xhr));
                $(evt.currentTarget).button('reset');

            },
        });

    },
});

var SystemHardwareDetailsEdit = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-hardware-details-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('input, select').first().focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        this.$('button').button('loading');
        var attributes = _.object(_.map(this.$('input, select'),
                function (elem) { return [elem.name, $(elem).val()]; }));
        this.model.save(
            attributes,
            {patch: true, wait: true,
             success: _.bind(this.save_success, this),
             error: _.bind(this.save_error, this)});
        evt.preventDefault();
    },
    save_success: function () {
        this.$el.modal('hide');
    },
    save_error: function (model, xhr) {
        this.$('.modal-footer').prepend(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

})();
