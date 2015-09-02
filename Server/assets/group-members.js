
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
        .done(function(){
             model.fetch();
        })
        .fail(function (jqxhr, status, error) {
             $(evt.currentTarget).button('reset');
             $.bootstrapGrowl('<h4>Failed to remove group member</h4> ' +
                   jqxhr.statusText + ': ' + jqxhr.responseText,
                     {type: 'error'});
         });
       evt.preventDefault();
     },
});

window.GroupMembersListView = Backbone.View.extend({
    template: JST['group-members-list'],
    initialize: function() {
        this.render();
        this.listenTo(this.model, 'change:members change:can_modify_membership', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (this.model.get('can_modify_membership')) {
            new GroupAddMemberForm({model: this.model}).$el
                .appendTo(this.$el);
        }
        var model = this.model;
        _.each(model.get('members'), function(member) {
            var view = new GroupMembersListItemView({model: model,
                                                     member: member});
            this.$('.group-members-list').append(view.el);
        });
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
            if (this.model.get('members')
                .find(function(m) { return m.get('user_name') == new_member })) {
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
        this.model.fetch();
        this.$('button').button('reset');
    },
    error: function (jqxhr, status, error) {
        this.$('button').button('reset');
        $.bootstrapGrowl('<h4>Failed to add group member</h4> ' +
              jqxhr.statusText + ': ' + jqxhr.responseText,
                {type: 'error'});
    },
});

})();
