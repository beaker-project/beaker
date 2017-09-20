
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.User = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="mailto:<%- email_address %>" title="<%- display_name %> &lt;<%- email_address %>&gt;"><%- user_name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    initialize: function (attributes, options) {
        options = options || {};
        if (options.url)
            this.url = options.url;
    },
    parse: function (data) {
        if (data['ssh_public_keys']) {
            var ssh_public_keys = this.get('ssh_public_keys') || new UserSSHPublicKeys([], {user: this});
            ssh_public_keys.reset(data['ssh_public_keys'], {parse: true});
            data['ssh_public_keys'] = ssh_public_keys;
        }
        if (data['submission_delegates']) {
            var submission_delegates = this.get('submission_delegates') || new UserSubmissionDelegates([], {user: this});
            submission_delegates.reset(data['submission_delegates'], {parse: true});
            data['submission_delegates'] = submission_delegates;
        }
        return data;
    },
    add_ssh_public_key: function (keytext) {
        var model = this;
        return $.ajax({
            url: this.url + '/ssh-public-keys/',
            type: 'POST',
            contentType: 'text/plain',
            data: keytext,
        }).then(function () {
            return model.fetch(); // refresh ssh_public_keys attribute
        });
    },
    add_submission_delegate: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/submission-delegates/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({user_name: user_name}),
        }).then(function () {
            return model.fetch(); // refresh submission_delegates attribute
        });
    },
    remove_submission_delegate: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/submission-delegates/?user_name=' + encodeURIComponent(user_name),
            type: 'DELETE',
        }).then(function () {
            return model.fetch(); // refresh submission_delegates attribute
        });
    },
    create_keystone_trust: function (data) {
        var model = this;
        return $.ajax({
            url: this.url + '/keystone-trust',
            type: 'PUT',
            dataType: 'json',
            contentType: 'application/json',
            data: JSON.stringify(data),
        }).then(function () {
            return model.fetch(); // refresh openstack_trust_id attribute
        });
    },
    delete_keystone_trust: function () {
        var model = this;
        return $.ajax({
            url: this.url + '/keystone-trust',
            type: 'DELETE',
        }).then(function () {
            return model.fetch(); // refresh openstack_trust_id attribute
        });
    },
});

var SSHPublicKey = Backbone.Model.extend({
});

var UserSSHPublicKeys = Backbone.Collection.extend({
    model: SSHPublicKey,
    initialize: function (attributes, options) {
        this.user = options.user;
    },
    url: function () {
        return _.result(this.user, 'url') + '/ssh-public-keys/';
    },
});

var UserSubmissionDelegates = Backbone.Collection.extend({
    model: User,
});

window.Users = BeakerPageableCollection.extend({
    model: User,
    initialize: function (attributes, options) {
        this.url = options.url;
    },
});

window.Group = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>groups/<%- encodeURIComponent(group_name) %>" title="<%- display_name %>"><%- group_name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    initialize: function (attributes, options) {
        if(options && options.url)
            this.url = options.url;
    },
    parse: function (data) {
        data['members'] = _.map(data['members'], function(user){ return new User(user); });
        data['excluded_users'] = _.map(data['excluded_users'], function(user){ return new User(user); });
        data['owners'] = _.map(data['owners'], function(user){ return new User(user); });
        data['access_policy'] = new SystemPoolAccessPolicy(data['access_policy'],
                {parse: true, system_pool: this});
        return data;
    },
    //TODO: use Backbone-relational.js or similar to handle model relationships.
    add_member: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/members/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'user_name': user_name}),
        }).then(function () {
            return model.fetch(); // refresh group membership
        });
    },
    remove_member: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/members/' + '?user_name=' + encodeURIComponent(user_name),
            type: 'DELETE',
            contentType: 'application/json',
        }).then(function () {
            return model.fetch(); // refresh group membership
        });
    },
    exclude_user: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/excluded-users/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'user_name': user_name}),
        }).then(function () {
            return model.fetch(); // refresh group membership
        });
    },
    //Remove a user from the list of excluded users in an inverted group.
    remove_excluded_user: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/excluded-users/' + '?user_name=' + encodeURIComponent(user_name),
            type: 'DELETE',
            contentType: 'application/json',
        }).then(function () {
            return model.fetch(); // refresh group membership
        });
    },
    add_owner: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/owners/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'user_name': user_name}),
        }).then(function () {
            return model.fetch(); // refresh group ownership
        });
    },
    remove_owner: function (user_name) {
        var model = this;
        return $.ajax({
            url: this.url + '/owners/' + '?user_name=' + encodeURIComponent(user_name),
            type: 'DELETE',
            contentType: 'application/json'
        }).then(function () {
            return model.fetch(); // refresh group ownership
        });
    },
    add_permission: function (permission) {
        var model = this;
        return $.ajax({
            url: this.url + '/permissions/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'permission_name': permission}),
        }).done(function () {
            // manually add it, cheaper than refreshing from the server
            model.set({'permissions': model.get('permissions').concat([permission])});
        });
    },
    remove_permission: function (permission) {
        var model = this;
        return $.ajax({
            url: this.url + '/permissions/' + '?permission_name=' + encodeURIComponent(permission),
            type: 'DELETE',
            contentType: 'application/json'
        }).done(function () {
            // manually remove it, cheaper than refreshing from the server
            model.set({'permissions': _.without(model.get('permissions'), permission)});
        });
    },
});

/** The collection of all Beaker groups. */
window.Groups = BeakerPageableCollection.extend({
    model: Group,
    initialize: function (attributes, options) {
        this.url = options.url;
    },
});

})();
