// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPoolAccessPolicyView = Backbone.View.extend({
    template: JST['system-pool-access-policy'],
    events: {
        'submit   form': 'submit',
        'reset    form': 'reset',
    },

    initialize: function (options) {
        this.render();
    },
    render: function () {
        this.rules_changed = false;
        this.request_in_progress = false;
        this.readonly = this.model.get('can_edit_policy') ? false : true;
        this.$el.html(this.template(_.extend({readonly: this.readonly}, this.model.attributes)));
        this.access_policy_table = new AccessPolicyView({
            model: this.model.get('access_policy'),
            el: this.$('div.access-policy'),
            readonly: this.readonly,
        });
        this.listenTo(this.access_policy_table, 'changed_access_policy_rules', this.mark_rules_changed);
    },

    mark_rules_changed: function () {
        this.rules_changed = true;
        this.update_button_state();
    },

    update_button_state: function () {
        this.$('.form-actions button').prop('disabled',
                !this.rules_changed || this.request_in_progress);
    },

    sync_error: function (model, xhr) {
        this.$('.sync-status').empty().append(alert_for_xhr(xhr));
        this.request_in_progress = false;
        this.update_button_state();
    },

    submit: function (evt) {
        evt.preventDefault();
        this.request_in_progress = true;
        this.update_button_state();
        this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Saving&hellip;');
        this.model.get('access_policy').save_access_policy({
            success: _.bind(this.render, this),
            error: _.bind(this.sync_error, this)});
    },

    reset: function (evt) {
        evt.preventDefault();
        this.request_in_progress = true;
        this.update_button_state();
        this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Loading&hellip;');
        this.model.fetch({
                success: _.bind(this.render, this),
                error: _.bind(this.sync_error, this)});
    },
});

})();
