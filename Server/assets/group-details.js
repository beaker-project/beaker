// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.GroupDetailsView = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    render: function () {
      new GroupPageHeaderView({model: this.model}).$el
          .appendTo(this.$el);
      new GroupRootPasswordView({model: this.model}).$el
          .appendTo(this.$el);
    },
});

window.GroupPageHeaderView = Backbone.View.extend({
    template: JST['group-page-header'],
    initialize: function () {
        this.listenTo(this.model, 'change:display_name change:can_edit', this.render);
        this.render();
    },
    events: {
        'click .edit': 'edit',
    },
    render: function () {
      this.$el.html(this.template(this.model.attributes));
    },
    edit: function () {
        new GroupEditModal({model: this.model});
    },
});

window.GroupRootPasswordView = Backbone.View.extend({
    id: 'root_pw_display',
    template: JST['group-rootpassword'],
    initialize: function () {
        this.listenTo(this.model, 'change:root_password change:can_view_rootpassword', this.render);
        this.render();
    },
    render: function function_name() {
      this.$el.html(this.template(this.model.attributes));
    },
});

var GroupEditModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['group-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=group_name]').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('input').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        if (model.get('can_edit_ldap') && model.get('ldap')) {
            this.$('input[name=ldap]').prop('checked', true);
        }
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var attributes = _.object(_.map(this.$('input'),
                function (elem) { return [elem.name, $(elem).val()]; }));
        if (this.model.get('can_edit_ldap')) {
          attributes['ldap'] = this.$('input[name=ldap]').prop('checked');
        }
        this.model.save(attributes,
            {patch: true, wait: true})
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        if (xhr.getResponseHeader('Location'))
            window.location = xhr.getResponseHeader('Location');
        else
            this.$el.modal('hide');
    },
    save_error: function (xhr) {
        $('<div class="alert alert-error"/>')
            .text(xhr.statusText + ': ' + xhr.responseText)
            .appendTo(this.$('.sync-status'));
        this.$('.modal-footer button').button('reset');
    },
});

})();
