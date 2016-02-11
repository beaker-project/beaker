
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemAccessPolicyView = Backbone.View.extend({
    template: JST['system-access-policy'],
    events: {
        'change   input[name=policy]': 'changed',
        'change   select[name=pool_name]': 'changed',
        'submit   form': 'submit',
        'reset    form': 'reset',
    },

    initialize: function (options) {
        this.listenTo(this.model, 'request', this.sync_started);
        this.listenTo(this.model, 'change:active_access_policy change:can_edit_policy change:pools', this.render);
        this.render();
    },

    render: function () {
        this.dirty = false;
        this.request_in_progress = false;
        this.readonly = this.model.get('can_edit_policy') ? false : true;
        this.$el.html(this.template(_.extend({readonly: this.readonly}, this.model.attributes)));
        this.$('[name=policy]').val([this.model.get('active_access_policy').type]);
        this.$('[name=pool_name]').val(this.model.get('active_access_policy').pool_name
                || this.model.get('pools')[0]);
        this.access_policy_table = new AccessPolicyView({
            model: this.model.get('access_policy'),
            el: this.$('div.access-policy'),
            readonly: this.readonly,
        });
        this.listenTo(this.access_policy_table, 'changed_access_policy_rules', this.changed);
        this.update_state();
    },

    update_state: function () {
        var selected_policy = this.$('[name=policy]:checked').val();
        if (!this.readonly) {
            // Disable pool policy selection if the system is not in any pool
            this.$('[name=policy][value=pool]').prop('disabled', _.isEmpty(this.model.get('pools')));
            // pool selection is disabled unless active policy type is pool or
            // the system is not in any pool
            this.$('[name=pool_name]').prop('disabled', selected_policy != 'pool' ||
                                            _.isEmpty(this.model.get('pools')));
            // buttons are disabled if nothing has changed, or if request is in progress
            this.$('.form-actions button').prop('disabled',
                    !this.dirty || this.request_in_progress);
        }
        // access policy table is hidden unless active policy type is custom
        this.access_policy_table.$el.toggle(selected_policy == 'custom');
    },

    changed: function () {
        this.dirty = true;
        this.update_state();
    },

    sync_started: function () {
        this.request_in_progress = true;
        this.update_state();
    },
    sync_complete: function () {
        this.request_in_progress = false;
        this.update_state();
        this.$('.sync-status').empty();
    },

    sync_error: function (xhr) {
        this.$('.sync-status').empty().append(alert_for_xhr(xhr));
        this.request_in_progress = false;
        this.update_state();
    },

    submit: function (evt) {
        evt.preventDefault();
        var policy_type = this.$('[name=policy]:checked').val();
        if (policy_type == 'pool') {
            var pool = this.$("select[name=pool_name]").val();
            this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Saving&hellip;');
            this.model.save({'active_access_policy': {'pool_name':pool}},
                            {patch: true, wait: true})
                .fail(_.bind(this.sync_error, this));
        } else if (policy_type == 'custom') {
            this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Saving&hellip;');
            var policy = this.model.get('access_policy');
            var model = this.model;
            var view = this;
            policy.save_access_policy()
                .then(function () {
                    view.access_policy_table.render();
                    return model.save(
                        {'active_access_policy': {'custom': true}},
                        {patch: true, wait: true});
                })
                .done(_.bind(this.sync_complete, this))
                .fail(_.bind(this.sync_error, this));
        }
    },

    reset: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').html('<i class="fa fa-spinner fa-spin"></i> Loading&hellip;');
        this.model.fetch({
                success: _.bind(this.render, this),
                error: _.bind(this.sync_error, this)});
    },
});

})();
