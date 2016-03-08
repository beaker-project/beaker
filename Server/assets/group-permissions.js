
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupPermissionsListItemView = Backbone.View.extend({
    tagName: 'li',
    template: JST['group-permissions-list-item'],
    events: {
        'click .permission-remove': 'remove_permission',
    },
    initialize: function(options) {
        this.permission = options.permission;
        this.render();
    },
    render: function() {
        this.$el.html(this.template({'permission': this.permission,
            'can_edit': this.model.get('can_edit')}));
    },
    remove_permission: function (evt) {
        var model = this.model;
        var permission = this.permission;
        $(evt.currentTarget).button('loading');
        model.remove_permission(this.permission)
          .fail(function (jqxhr, status, error) {
                growl_for_xhr(jqxhr, 'Failed to remove group permission');
          });
        $(evt.currentTarget).button('reset');
        evt.preventDefault();
     },
});

window.GroupPermissionsListView = Backbone.View.extend({
    template: JST['group-permissions-list'],
    initialize: function() {
        this.render();
        this.listenTo(this.model,
            'change:permissions change:can_add_permission change:can_edit', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (this.model.get('can_add_permission')) {
            new GroupAddPermissionForm({model: this.model}).$el
                .appendTo(this.$el);
        }
        var model = this.model;
        _.each(model.get('permissions'), function(permission) {
            var view = new GroupPermissionsListItemView({model: model,
                                                    permission: permission});
            this.$('.group-permissions-list').append(view.el);
        });
    }
});

var GroupAddPermissionForm = Backbone.View.extend({
    template: JST['group-add-permission'],
    events: {
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name="group_permission"]').beaker_typeahead('permission-name');
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            this.$('.alert').remove();
            var new_permission = this.$('input[name=group_permission]').val();
            if (_.contains(this.model.get('permissions'), new_permission)) {
                // nothing to do
                this.$('input[name="group_permission"]').typeahead('setQuery', '');
                return false;
            }
            this.$('button').button('loading');
            var model = this.model;
            model.add_permission(new_permission)
                .done(function () {
                    $(evt.currentTarget).button('reset');
                })
                .fail(_.bind(this.error, this));
        }
        evt.preventDefault();
    },
    error: function (jqxhr, status, error) {
        this.$('button').button('reset');
        this.$el.append(alert_for_xhr(jqxhr));
    },
});

})();
