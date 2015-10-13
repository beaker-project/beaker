
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
});

window.Group = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>groups/<%- group_name %>" title="<%- display_name %>"><%- group_name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    initialize: function (attributes, options) {
        if(options && options.url)
            this.url = options.url;
    },
    parse: function (data) {
        data['members'] = _.map(data['members'], function(user){ return new User(user); });
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
