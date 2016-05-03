
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * Given the raw (plain text) whiteboard, returns the first paragraph of the 
 * the whiteboard with all markup stripped, truncated to 100 characters.
 */
window.truncated_whiteboard = function (raw_whiteboard) {
    if (!_.isNull(raw_whiteboard)) {
        var length_limit = 100;
        var rendered = $('<body/>').html(marked(raw_whiteboard,
                {sanitize: true, smartypants: false}));
        var first_line = rendered.find('p:first').text();
        if (first_line.length > 100)
            first_line = first_line.substr(0, 99) + '\u2026';
        return first_line;    
    } 
};

window.JobHeaderView = Backbone.View.extend({
    tagName: 'div',
    className: 'job-header',
    template: JST['job-header'],
    events: {
        'click .edit': 'edit',
        'click .cancel': 'cancel',
        'click .delete': 'delete',
    },
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.listenTo(this.model, 'cancelling', this.cancelling);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var title = this.model.get('t_id');
        if (this.model.get('whiteboard'))
            title += ' \u00b7 ' + truncated_whiteboard(this.model.get('whiteboard'));
        title += ' \u00b7 ' + this.model.get('status') + '/' + this.model.get('result');
        document.title = title;
    },
    edit: function () {
        new JobEditModal({model: this.model});
    },
    cancel: function () {
        new JobCancelModal({model: this.model});
    },
    cancelling: function () {
        this.$('button.cancel').button('loading');
    },
    'delete': function () {
        var model = this.model, $del_btn = this.$('button.delete');
        $del_btn.button('loading');
        bootbox.confirm_as_promise('<p>Are you sure you want to delete this job?</p>')
            .fail(function () { $del_btn.button('reset'); })
            .then(function () { return model.destroy(); })
            .fail(_.bind(this.delete_error, this))
            .done(function () { window.location = beaker_url_prefix + 'jobs/mine'; });
    },
    delete_error: function(xhr) {
        if (!_.isEmpty(xhr)) {
            growl_for_xhr(xhr, 'Failed to delete');
            this.$('button.delete').button('reset');
        }
    },
});

var JobEditModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['job-edit'],
    events: {
        'change select[name=retention_tag]': 'retention_tag_changed',
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=whiteboard]').focus();
    },
    retention_tag_changed: function () {
        // Does the newly selected retention tag require/permit a product
        // association?
        var selection = this.$('[name=retention_tag]').val();
        var needs_product = _.findWhere(
                this.model.get('possible_retention_tags'),
                {'tag': selection}).needs_product;
        this.$('[name=product]')
            .prop('disabled', !needs_product)
            .selectpicker('refresh');
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('[name=whiteboard]').val(model.get('whiteboard'));
        this.$('[name=retention_tag]').val(model.get('retention_tag'));
        if (model.has('product'))
            this.$('[name=product]').val(model.get('product'));
        this.$('[name=cc]').val(model.get('cc').join('; '));
        this.$('select').selectpicker();
        this.retention_tag_changed();
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var attributes = {
            whiteboard: this.$('[name=whiteboard]').val(),
            cc: (!_.isEmpty(this.$('[name=cc]').val().trim())
                ? this.$('[name=cc]').val().trim().split(/[;\s]+/)
                : []),
            retention_tag: this.$('[name=retention_tag]').val(),
            product: (!this.$('[name=product]').is(':disabled')
                     ? this.$('[name=product]').val()
                     : null), // send null to clear product
        };
        this.model.save(attributes, {patch: true, wait: true})
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        this.$el.modal('hide');
    },
    save_error: function (xhr) {
        alert_for_xhr(xhr).appendTo(this.$('.sync-status'));
        this.$('.modal-footer button').button('reset');
    },
});

var JobCancelModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['job-cancel'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=message]').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var message = this.$('[name=message]').val();
        this.model.cancel(message)
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        this.$el.modal('hide');
    },
    save_error: function (xhr) {
        alert_for_xhr(xhr).appendTo(this.$('.sync-status'));
        this.$('.modal-footer button').button('reset');
    },
});

})();
