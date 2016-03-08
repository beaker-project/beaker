
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemPoolInfo = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    render: function () {
        new SystemPoolHeading({model: this.model}).$el
            .appendTo(this.$el);
        new SystemPoolDescription({model: this.model}).$el
            .appendTo(this.$el);
    },
});

window.SystemPoolHeading = Backbone.View.extend({
    template: JST['system-pool-heading'],
    initialize: function () {
        this.listenTo(this.model, 'change:owner', this.render);
        this.render();
    },
    events: {
        'click .edit': 'edit',
        'click .delete': 'delete',
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    edit: function () {
        new SystemPoolEditModal({model: this.model});
    },
    'delete': function () {
        var model = this.model, $del_btn = this.$('button.delete');
        $del_btn.button('loading');
        bootbox.confirm_as_promise('<p>Are you sure you want to delete this pool?</p>')
            .fail(function () { $del_btn.button('reset'); })
            .then(function () { return model.destroy(); })
            .fail(_.bind(this.delete_error, this))
            .done(function () { window.location = beaker_url_prefix + 'pools/'; });
    },
    delete_error: function(xhr) {
        if (!_.isEmpty(xhr)) {
            growl_for_xhr(xhr, 'Failed to delete');
            this.$('button.delete').button('reset');
        }
    },
});

window.SystemPoolDescription = Backbone.View.extend({
    initialize: function () {
        this.listenTo(this.model, 'change:description', this.render);
        this.render();
    },
    render: function () {
        var description = this.model.get('description');
        if (description) {
            this.$el.html(marked(this.model.get('description'),
                    {sanitize: true, smartypants: true}));
        } else {
            this.$el.empty();
        }
        return this;
    },
});

var SystemPoolEditModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-pool-edit'],
    events: {
        'change select[name=owner_type]': 'owner_type_changed',
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=description]').focus();
    },
    owner_type_changed: function () {
        // We also disable the invisible inputs so that the browser doesn't 
        // force validation for them.
        switch (this.$('[name=owner_type]').val()) {
            case 'user':
                this.$('input[name="group_name"]').prop('disabled', true).hide();
                this.$('input[name="user_name"]').prop('disabled', false).show().focus();
                break;
            case 'group':
                this.$('input[name="user_name"]').prop('disabled', true).hide();
                this.$('input[name="group_name"]').prop('disabled', false).show().focus();
                break;
        }
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('[name=name]').val(model.get('name'));
        this.$('[name=description]').val(model.get('description'));
        if (model.get('owner').has('group_name')) {
            this.$('[name=owner_type]').val('group');
            this.$('[name=group_name]').val(model.get('owner').get('group_name'));
        } else {
            this.$('[name=owner_type]').val('user');
            this.$('[name=user_name]').val(model.get('owner').get('user_name'));
        }
        this.$('select').selectpicker();
        this.$('input[name="user_name"]').beaker_typeahead('user-name');
        this.$('input[name="group_name"]').beaker_typeahead('group-name');
        this.owner_type_changed();
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var attributes = {
            'name': this.$('input[name=name]').val(),
            'description': this.$('textarea[name=description]').val(),
        }
        switch (this.$('[name=owner_type]').val()) {
            case 'user':
                attributes['owner'] = new User({user_name: this.$('[name=user_name]').val()});
                break;
            case 'group':
                attributes['owner'] = new Group({group_name: this.$('[name=group_name]').val()});
                break;
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
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('.modal-footer button').button('reset');
    },
});

})();
