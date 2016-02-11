// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {
window.LabController = Backbone.Model.extend({
    initialize: function (attributes, options) {
        // Upon creation the API expects a POST against /labcontrollers. If we
        // just set idAttribute to fqdn, it would issue a PATCH against
        // /labcontrollers/<fqdn> since it's set upon creation. When we edit
        // existing lab controllers however, we want the URL to send the updates
        // against /labcontrollers/<fqdn> instead of /labcontrollers/<id>
        this.listenTo(this, 'change:fqdn sync', function (model) {
            this.url = this.collection.url + this.get('fqdn');
        });
        if (! this.isNew()) {
            this.url = this.collection.url + this.get('fqdn');
        }
    }
});

window.LabControllers = Backbone.Collection.extend({
    model: LabController,
    initialize: function (attributes, options) {
        this.url = options.url;
        this.comparator = 'fqdn';
    },
});

var LabControllerListItem = Backbone.View.extend({
    tagName: 'li',
    template: JST['labcontroller'],
    events: {
        'click .labcontroller-remove': 'remove_labcontroller',
        'click .labcontroller-restore': 'restore_labcontroller',
        'click .labcontroller-edit': 'update_labcontroller',
    },
    initialize: function(options) {
        this.listenTo(this.model, 'change', this.render);
        this.options = options;
        this.render();
    },
    render: function() {
        var data = _.extend({can_edit: this.options['can_edit'] || false}, this.model.toJSON());
        this.$el.html(this.template(data));
    },
    update_labcontroller: function (evt) {
        new EditLabControllerModal({model: this.model});
    },
    restore_labcontroller: function (evt) {
        $(evt.currentTarget).button('loading');
        this.model.save({removed: false},
                        {wait: true,
                            patch: true})
            .done(_.bind(this.labcontroller_restored, this))
            .fail(_.bind(this.on_error, this));
        evt.preventDefault();
    },
    labcontroller_restored: function() {
        this.model.fetch();
        this.render();
    },
    remove_labcontroller: function (evt) {
        $(evt.currentTarget).button('loading');
        var msg = (
            '<p>Are you sure you want to remove ' + this.model.get('fqdn') + '?</p>'
            + '<p>Any systems attached to this lab controller will be detached, '
            + 'running recipes cancelled and associated distro trees removed.</p>');
        return bootbox.confirm_as_promise(msg)
            .fail(function() {$(evt.currentTarget).button('reset');})
            .done(_.bind(this.removal_confirmed, this));
    },
    removal_confirmed: function () {
        return this.model.save({removed: true},
                                {wait: true,
                                patch: true,
                                error: _.bind(this.on_error, this)});
    },
    on_error: function (model, xhr) {
        this.$('button').button('reset');
        // Inconsistent: Using growl here, since appending an error div to the list item will be worse.
        growl_for_xhr(xhr, 'Error removing lab controller');
    },
})

window.LabControllersView = Backbone.View.extend({
    initialize: function(options) {
        this.options = options;
        this.render();
        this.listenTo(this.collection, 'add', this.render);
        this.listenTo(this.collection, 'remove', this.render);
    },
    render: function () {
        this.$el.empty();
        this.collection.each(function(labcontroller) {
            var view = new LabControllerListItem({model: labcontroller,
                                                    can_edit: this.options['can_edit'] || false});
            this.$el.append(view.el);
        }, this);
        return this;
    },
});

window.LabControllersManageView = Backbone.View.extend({
    template: JST['labcontroller-add'],
    events: {
        'click .labcontroller-add': 'add',
    },
    initialize: function(options) {
        this.options = options;
        this.render();
    },
    render: function() {
        this.$el.html(this.template(this.options));
    },
    add: function() {
        new CreateLabControllerModal({collection: this.collection});
    }
});

var CreateLabControllerModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['labcontroller-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function(options) {
        this.options = options
        this.render();
        this.$el.modal();
        this.$('[name=fqdn]').focus();
    },
    render: function() {
        this.$el.html(this.template({title: 'Create Lab Controller', show_disabled: false}));
    },
    submit: function(evt) {
        evt.preventDefault();
        var fqdn = this.$('input[type=text][name=fqdn]').val();
        this.$('button').button('loading');

        this.collection.create(
            {fqdn: fqdn,
                user_name: this.$('input[name=user_name]').val(),
                password: this.$('input[name=password]').val(),
                email_address: this.$('input[name=email_address]').val()
            },
            {wait: true,
                success: _.bind(this.success, this),
                error: _.bind(this.error, this)});
    },
    reset_button: function() {
        this.$('button').button('reset');
    },
    success: function(model, xhr) {
        this.reset_button();
        this.$('input[type=text]').val('');
        this.$el.modal('hide');
    },
    error: function(model, xhr) {
        this.reset_button();
        this.$el.append(alert_for_xhr(xhr));
    }
});

var EditLabControllerModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['labcontroller-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function(options) {
        this.options = options;
        this.render();
        this.$el.modal();
        this.$('[name=fqdn]').focus();
    },
    render: function() {
        var fqdn = this.model.get('fqdn')
        var data = _.extend({title: 'Edit ' + fqdn, show_disabled: true}, this.model.toJSON());
        this.$el.html(this.template(data));
        this.$('input[name=fqdn]').val(fqdn);
        this.$('input[name=user_name]').val(this.model.get('user_name'));
        this.$('input[name=email_address]').val(this.model.get('email_address'));
        if (this.model.get('disabled')) {
            this.$('input[name=disabled]').prop('checked', true);
        }
    },
    submit: function(evt) {
        evt.preventDefault();
        this.$('button').button('loading');
        data = {
            fqdn: this.$('input[name=fqdn]').val(),
            user_name: this.$('input[name=user_name]').val(),
            email_address: this.$('input[name=email_address]').val(),
            disabled: this.$('input[name=disabled]').prop('checked'),
        }
        var password = this.$('input[name=password]').val();
        if (password) {
            data.password = password;
        }

        this.model.save(data, {
            wait: true,
            patch: true,
            success: _.bind(this.success, this),
            error: _.bind(this.error, this)});
    },
    reset_button: function() {
        this.$('button').button('reset');
    },
    success: function(response, status, xhr) {
        this.reset_button();
        this.$el.modal('hide');
    },
    error: function(model, xhr) {
        this.reset_button();
        this.$el.append(alert_for_xhr(xhr));
    }
})
})();
