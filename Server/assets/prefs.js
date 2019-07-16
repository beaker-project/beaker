
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.UserRootPasswordView = Backbone.View.extend({
    template: JST['user-root-password'],
    events: {
        'submit form': 'save',
    },
    initialize: function (options) {
        this.default_root_password = options.default_root_password;
        this.default_root_passwords = options.default_root_passwords;
        this.render();
        this.listenTo(this.model, 'change', this.render);
    },
    render: function () {
        var html = this.template(this.model.attributes) +
                JST['default-root-password']({
                    default_root_password: this.default_root_password,
                    default_root_passwords: this.default_root_passwords,
                });
        this.$el.html(html);
    },
    save: function (evt) {
        evt.preventDefault();
        var $form = this.$('form');
        $form.find('button').button('loading');
        $form.find('.alert-error').remove();
        var new_root_password = $form.find('[name=root_password]').val();
        this.model.save({root_password: new_root_password}, {patch: true, wait: true})
            .always(function () { $form.find('button').button('reset'); })
            .fail(function (xhr) { $form.append(alert_for_xhr(xhr)); });
    },
});

window.UserSSHPublicKeysView = Backbone.View.extend({
    template: JST['user-ssh-public-keys'],
    events: {
        'submit form.add': 'add',
    },
    initialize: function() {
        this.render();
        this.listenTo(this.model.get('ssh_public_keys'), 'add remove reset', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('.ssh-public-keys-list').append(this.model.get('ssh_public_keys').map(
                function (item) { return new UserSSHPublicKeyListItem({model: item}).el; }));
    },
    add: function (evt) {
        evt.preventDefault();
        var $form = $(evt.currentTarget), $el = this.$el;
        $form.find('button').button('loading');
        this.$('.alert-error').remove();
        this.model.add_ssh_public_key(this.$('[name=key]').val())
            .always(function () { $form.find('button').button('reset'); })
            .fail(function (xhr) { $el.append(alert_for_xhr(xhr)); });
    },
});

var UserSSHPublicKeyListItem = Backbone.View.extend({
    tagName: 'li',
    template: JST['user-ssh-public-key-list-item'],
    events: {
        'click .remove': 'remove',
    },
    initialize: function() {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    remove: function (evt) {
        var $el = this.$el;
        this.$('button').button('loading');
        this.model.destroy({wait: true})
            .always(function () { $el.find('button').button('reset'); })
            .fail(function (xhr) {
                // show it in a growl because we can't cram it inside the list item
                growl_for_xhr(xhr, 'Failed to remove SSH public key');
            });
    },
});

window.UserSubmissionDelegatesView = Backbone.View.extend({
    template: JST['user-submission-delegates'],
    events: {
        'click button.remove': 'remove',
        'submit form.add': 'add',
    },
    initialize: function() {
        this.render();
        this.listenTo(this.model.get('submission_delegates'), 'add remove reset', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('[name=user_name]').beaker_typeahead('user-name');
        // Focus the username input, but only if it's visible. (We might be
        // showing another tab right now.)
        this.$('[name=user_name]:visible').focus();
    },
    add: function (evt) {
        evt.preventDefault();
        var $form = $(evt.currentTarget), $el = this.$el;
        this.$('.alert-error').remove();
        var new_delegate = this.$('[name=user_name]').val();
        if (this.model.get('submission_delegates').find(
                function (u) { return u.get('user_name') == new_delegate; })) {
            // nothing to do
            this.$('[name=user_name]').typeahead('setQuery', '');
            return;
        }
        $form.find('button').button('loading');
        this.model.add_submission_delegate(this.$('[name=user_name]').val())
            .always(function () { $form.find('button').button('reset'); })
            .fail(function (xhr) { $el.append(alert_for_xhr(xhr)); });
    },
    remove: function (evt) {
        var $button = $(evt.currentTarget);
        $button.button('loading');
        this.model.remove_submission_delegate($button.data('username'))
            .always(function () { $button.button('reset'); })
            .fail(function (xhr) {
                // show it in a growl because we can't cram it inside the list item
                growl_for_xhr(xhr, 'Failed to remove submission delegate');
            });
    },
});

window.UserUIPreferencesView = Backbone.View.extend({
    template: JST['user-ui-preferences'],
    events: {
        'click input': 'changed',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function () {
        this.render();
        this.listenTo(this.model, 'change:use_old_job_page', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('[name=use_old_job_page]').prop('checked',
                this.model.get('use_old_job_page'));
        this.$('.form-actions button').prop('disabled', true);
    },
    changed: function () {
        this.$('.form-actions button').prop('disabled', false);
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.alert-error').remove();
        this.$('.form-actions button').button('loading');
        var $el = this.$el;
        this.model.save(
                {use_old_job_page: this.$('[name=use_old_job_page]').is(':checked')},
                {patch: true, wait: true})
            .always(function () {
                $el.find('.form-actions button').button('reset');
            })
            .fail(function (xhr) {
                $el.append(alert_for_xhr(xhr));
            })
            .done(function (xhr) {
                // Bootstrap's button reset happens in setTimeout for...
                // questionable reasons, so we have to do the same here.
                setTimeout(function () {
                    $el.find('.form-actions button').prop('disabled', true);
                }, 0);
            });
    },
    reset: function (evt) {
        evt.preventDefault();
        this.$('[name=use_old_job_page]').prop('checked',
                this.model.get('use_old_job_page'));
        this.$('.form-actions button').prop('disabled', true);
    },
});

window.UserNotificationsView = Backbone.View.extend({
    template: JST['user-notifications'],
    events: {
        'click input': 'changed',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function() {
        this.render();
        this.listenTo(this.model, 'change', this.render);
    },
    render: function() {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        this.$('input:checkbox').each(function (i, elem) {
            $(elem).prop('checked', model.get(elem.name));
        });
        this.$('.form-actions button').prop('disabled', true);
    },
    changed: function() {
        this.$('.form-actions button').prop('disabled', false);
    },
    submit: function(evt) {
        evt.preventDefault();
        this.$('.alert-error').remove();
        this.$('.form-actions button').button('loading');
        var $el = this.$el;
        var attributes = {
            'notify_job_completion': this.$(
                'input[name=notify_job_completion]').is(':checked'),
            'notify_broken_system': this.$(
                'input[name=notify_broken_system]').is(':checked'),
            'notify_system_loan': this.$(
                'input[name=notify_system_loan]').is(':checked'),
            'notify_group_membership': this.$(
                'input[name=notify_group_membership]').is(':checked'),
            'notify_reservesys': this.$(
                'input[name=notify_reservesys]').is(':checked'),
        };
        this.model.save(attributes, {patch: true, wait: true})
            .always(function () {
                $el.find('.form-actions button').button('reset');
            })
            .fail(function (xhr) {
                $el.append(alert_for_xhr(xhr));
            })
            .done(function (xhr) {
                // Bootstrap's button reset happens in setTimeout for...
                // questionable reasons, so we have to do the same here.
                // https://github.com/twbs/bootstrap/issues/6242
                setTimeout(function () {
                    $el.find('.form-actions button').prop('disabled', true);
                }, 0);
            });
    },
    reset: function (evt) {
        evt.preventDefault();
        this.render();
    },
});

window.UserKeystoneTrustView = Backbone.View.extend({
    template: JST['user-keystone-trust'],
    events: {
        'click input': 'changed',
        'click .delete': 'delete',
        'submit form': 'submit',
        'reset form': 'reset',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:openstack_trust_id', this.render);
        this.render();
    },
    changed: function () {
        this.$('.form-actions button').prop('disabled', false);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('.form-actions button').prop('disabled', true);
    },
    delete: function () {
        var model = this.model, $del_btn = this.$('button.delete');
        $del_btn.button('loading');
        bootbox.confirm_as_promise('<p>Are you sure you want to delete this trust?</p>')
            .fail(function () { $del_btn.button('reset'); })
            .then(function () { return model.delete_keystone_trust(); })
            .fail(_.bind(this.delete_error, this))
            .done(function () {
                $.bootstrapGrowl('<h4>Keystone trust has been deleted</h4>' +
                        'Your keystone trust has been successfully deleted.',
                        {type: 'success'});
            });
    },
    delete_error: function(xhr) {
        if (!_.isEmpty(xhr)) {
            growl_for_xhr(xhr, 'Failed to delete');
            this.$('button.delete').button('reset');
        }
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.alert-error').remove();
        this.$('.form-actions button').button('loading');
        var $el = this.$el;
        var attributes = {
            openstack_username: this.$('[name=openstack_username]').val(),
            openstack_password: this.$('[name=openstack_password]').val(),
            openstack_project_name: this.$('[name=openstack_project_name]').val(),
            openstack_project_domain_name: this.$('[name=openstack_project_domain_name]').val()
                || this.$('[name=openstack_project_domain_name]').attr('placeholder'),
            openstack_user_domain_name: this.$('[name=openstack_user_domain_name]').val()
                || this.$('[name=openstack_user_domain_name]').attr('placeholder'),
        };
        this.model.create_keystone_trust(attributes)
            .always(function () {
                $el.find('.form-actions button').button('reset');
            })
            .fail(function (xhr) {
                $el.append(alert_for_xhr(xhr));
            })
            .done(function (xhr) {
                // Bootstrap's button reset happens in setTimeout for...
                // questionable reasons, so we have to do the same here.
                setTimeout(function () {
                    $el.find('.form-actions button').prop('disabled', true);
                }, 0);
            });
    },
    reset: function (evt) {
        evt.preventDefault();
        this.$('input').each(function (i, elem) {
            $(elem).val('');
        });
    },
});

})();
