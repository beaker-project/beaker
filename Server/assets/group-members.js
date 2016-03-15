
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupMembersListItemView = Backbone.View.extend({
    tagName: 'li',
    template: JST['group-members-list-item'],
    events: {
        'click .member-remove': 'remove_member',
    },
    initialize: function(options) {
        this.member = options.member;
        this.render();
    },
    render: function() {
        this.$el.html(this.template({'user': this.member,
            'can_modify_membership': this.model.get('can_modify_membership')}));
    },
    remove_member: function (evt) {
       var model = this.model;
       $(evt.currentTarget).button('loading');
       model.remove_member(this.member.get('user_name'))
        .fail(function (jqxhr, status, error) {
             $(evt.currentTarget).button('reset');
             growl_for_xhr(jqxhr, 'Failed to remove group member');
         });
       evt.preventDefault();
     },
});

window.GroupExcludedUsersListItemView = Backbone.View.extend({
    tagName: 'li',
    template: JST['group-excluded-users-list-item'],
    events: {
        'click .excluded-user-remove': 'remove_excluded_user',
    },
    initialize: function(options) {
        this.user = options.user;
        this.render();
    },
    render: function() {
        this.$el.html(this.template({'user': this.user,
            'can_modify_membership': this.model.get('can_modify_membership')}));
    },
    remove_excluded_user: function (evt) {
       var model = this.model;
       $(evt.currentTarget).button('loading');
       model.remove_excluded_user(this.user.get('user_name'))
        .fail(function (jqxhr, status, error) {
             $(evt.currentTarget).button('reset');
             growl_for_xhr(jqxhr, 'Failed to remove user');
         });
       evt.preventDefault();
     },
});

window.GroupMembersListView = Backbone.View.extend({
    template: JST['group-members-list'],
    initialize: function() {
        this.render();
        this.listenTo(this.model,
          'change:members change:can_modify_membership change:excluded_users change:membership_type',
          this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        var membership_type = model.get('membership_type');
        if (membership_type == 'inverted') {
            if (this.model.get('can_modify_membership')) {
                new GroupExcludeUserForm({model: this.model}).$el
                    .appendTo(this.$el);
            }
            var excluded_users = _.sortBy(this.model.get('excluded_users'),
                function (m) { return m.get('user_name'); });
            _.each(excluded_users, function(user) {
                var view = new GroupExcludedUsersListItemView({model: model,
                                                         user: user});
                this.$('.group-excluded-users-list').append(view.el);
            });
        } else {
            if (this.model.get('can_modify_membership')) {
                new GroupAddMemberForm({model: this.model}).$el
                    .appendTo(this.$el);
            }
            var members = _.sortBy(this.model.get('members'), function (m) { return m.get('user_name'); });
            _.each(members, function(member) {
                var view = new GroupMembersListItemView({model: model,
                                                         member: member});
                this.$('.group-members-list').append(view.el);
            });
        }
    },
});

var GroupAddMemberForm = Backbone.View.extend({
    template: JST['group-add-member'],
    events: {
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name="group_member"]').beaker_typeahead('user-name');
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            this.$('.alert').remove();
            var new_member = this.$('input[name=group_member]').val();
            if (_.find(this.model.get('members'),
                function(m) { return m.get('user_name') == new_member })) {
                // nothing to do
                this.$('input[name="group_member"]').typeahead('setQuery', '');
                return false;
            }
            this.$('button').button('loading');
            this.model.add_member(new_member)
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

var GroupExcludeUserForm = Backbone.View.extend({
    template: JST['group-exclude-user'],
    events: {
        'submit form': 'submit',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name="group_user"]').beaker_typeahead('user-name');
    },
    submit: function (evt) {
        if (evt.currentTarget.checkValidity()) {
            this.$('.alert').remove();
            var user = this.$('input[name=group_user]').val();
            if (this.model.get('excluded_users')
                .find(function(m) { return m.get('user_name') == user })) {
                // nothing to do
                this.$('input[name="group_user"]').typeahead('setQuery', '');
                return false;
            }
            this.$('button').button('loading');
            this.model.exclude_user(user)
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
