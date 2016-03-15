
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupOwnersListItemView = Backbone.View.extend({
    tagName: 'li',
    template: JST['group-owners-list-item'],
    events: {
        'click .owner-remove': 'remove_owner',
    },
    initialize: function(options) {
        this.owner = options.owner;
        this.render();
    },
    render: function() {
        this.$el.html(this.template({'user': this.owner,
            'can_edit': this.model.get('can_edit')}));
    },
    remove_owner: function (evt) {
       var model = this.model;
       $(evt.currentTarget).button('loading');
       model.remove_owner(this.owner.get('user_name'))
        .fail(function (jqxhr, status, error) {
             $(evt.currentTarget).button('reset');
             growl_for_xhr(jqxhr, 'Failed to remove group owner');
         });
       evt.preventDefault();
     },
});

window.GroupOwnersListView = Backbone.View.extend({
    template: JST['group-owners-list'],
    initialize: function() {
        this.render();
        this.listenTo(this.model, 'change:owners change:can_modify_ownership', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (this.model.get('can_modify_ownership')) {
            new GroupAddOwnerForm({model: this.model}).$el
                .appendTo(this.$el);
        }
        var owners = _.sortBy(this.model.get('owners'), function (o) { return o.get('user_name'); });
        var model = this.model;
        _.each(owners, function(owner) {
            var view = new GroupOwnersListItemView({model: model,
                                                    owner: owner});
            this.$('.group-owners-list').append(view.el);
        });
    }
});

var GroupAddOwnerForm = Backbone.View.extend({
    template: JST['group-add-owner'],
    events: {
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name="group_owner"]').beaker_typeahead('user-name');
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            this.$('.alert').remove();
            var new_owner = this.$('input[name=group_owner]').val();
            if (_.find(this.model.get('owners'),
                function(o) { return o.get('user_name') == new_owner })) {
                // nothing to do
                this.$('input[name=group_owner]').typeahead('setQuery', '');
                return false;
            }
            this.$('button').button('loading');
            this.model.add_owner(new_owner)
               .done(_.bind(this.success, this))
               .fail(_.bind(this.error, this));
        }
        evt.preventDefault();
    },
    success: function () {
        this.$('button').button('reset');
    },
    error: function (jqxhr, status, error) {
        this.$('button').button('reset');
        this.$el.append(alert_for_xhr(jqxhr));
    },
});

})();
