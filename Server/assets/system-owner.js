
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemOwnerView = Backbone.View.extend({
    template: JST['system-owner'],
    events: {
        'click .change': 'change_owner',
        'click .cc-remove': 'remove_cc',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:owner change:notify_cc', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (this.model.get('can_change_notify_cc')) {
            this.$('.system-notify-cc').after(
                new SystemAddCcForm({model: this.model}).el);
        }
    },
    change_owner: function () {
        new SystemOwnerChangeModal({model: this.model});
    },
    remove_cc: function (evt) {
        $(evt.currentTarget).button('loading');
        this.model.remove_cc($(evt.currentTarget).data('cc'),
            {error: _.bind(this.remove_cc_error, this)});
        evt.preventDefault();
    },
    remove_cc_error: function (model, xhr) {
        $(evt.currentTarget).button('reset');
        this.$el.append(alert_for_xhr(xhr));
    },
});

var SystemAddCcForm = Backbone.View.extend({
    template: JST['system-add-cc'],
    events: {
        'change input[name=cc]': 'update_button_state',
        'input input[name=cc]': 'update_button_state',
        'keyup input[name=cc]': 'update_button_state',
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('button[type=submit]').prop('disabled', true);
    },
    update_button_state: function () {
        var $input = this.$('input[name=cc]');
        var allow_submission = ($input.val() && $input.get(0).checkValidity());
        this.$('button[type=submit]').prop('disabled', this.saving || !allow_submission);
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            var new_cc = this.$('input[name=cc]').val();
            if (_.contains(this.model.get('notify_cc'), new_cc)) {
                // nothing to do
                this.$('input[name=cc]').val('');
                return false;
            }
            this.saving = true;
            this.$('button').button('loading');
            this.model.add_cc(new_cc, {error: _.bind(this.error, this)});
        }
        evt.preventDefault();
    },
    error: function (model, xhr) {
        this.$el.append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

var SystemOwnerChangeModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-owner-change'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input[name="user_name"]').beaker_typeahead('user-name').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        this.model.save(
            {owner: {user_name: this.$('input[name=user_name]').val()}},
            {patch: true, wait: true,
             success: _.bind(this.save_success, this),
             error: _.bind(this.save_error, this)});
        evt.preventDefault();
    },
    save_success: function () {
        this.$el.modal('hide');
    },
    save_error: function (model, xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

})();
