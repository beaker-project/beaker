
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupCreateModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['group-create'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function (options) {
        this.can_create_ldap = options.can_create_ldap;
        this.render();
        this.$el.modal();
        this.$('[name=group_name]').focus();
    },
    render: function () {
        this.$el.html(this.template({can_create_ldap: this.can_create_ldap}));
        this.$('select').selectpicker();
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var attributes = {
            group_name: this.$('[name=group_name]').val(),
            display_name: this.$('[name=display_name]').val(),
            membership_type: this.$('[name=membership_type]').val(),
        };
        var new_group = new this.collection.model(attributes,
                {collection: this.collection});
        new_group.save()
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        window.location = xhr.getResponseHeader('Location');
    },
    save_error: function (xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('.modal-footer button').button('reset');
    },
});

})();
