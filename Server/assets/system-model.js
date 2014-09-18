
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * System-related models for client-side Backbone widgets.
 */

// XXX this needs to be moved somewhere better
window.User = Backbone.Model.extend({});

window.Loan = Backbone.Model.extend({
    parse: function (data) {
        data['recipient'] = !_.isEmpty(data['recipient']) ? new User(data['recipient']) : null;
        return data;
    },
});

window.Reservation = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

var AccessPolicyRule = Backbone.Model.extend({
    // ensure the 'everybody' attribute is filled in
    initialize: function (attributes, options) {
        if (!_.has(attributes, 'everybody')) {
            this.set('everybody', (attributes['user'] == null && 
                    attributes['group'] == null));
        }
    },
});

var AccessPolicyRules = Backbone.Collection.extend({
    model: AccessPolicyRule,
});

window.AccessPolicy = Backbone.Model.extend({
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'access-policy';
    },
    parse: function (data) {
        data['rules'] = (!_.isEmpty(data['rules']) ?
                new AccessPolicyRules(data['rules'], {parse: true}) : null);
        return data;
    },
});

window.Command = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

window.CommandQueue = Backbone.PageableCollection.extend({
    model: Command,
    state: {
        pageSize: 20,
    },
    queryParams: {
        currentPage: 'page',
        pageSize: 'page_size',
        totalPages: null,
        totalRecords: null,
        sortKey: 'sort_by',
        order: 'order',
    },
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'commands/';
    },
    parseState: function (response) {
        return {totalRecords: response.count};
    },
    parseRecords: function (response) {
        return response.entries;
    },
});

window.SystemActivityEntry = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

window.SystemActivity = Backbone.PageableCollection.extend({
    model: SystemActivityEntry,
    state: {
        pageSize: 20,
    },
    queryParams: {
        currentPage: 'page',
        pageSize: 'page_size',
        totalPages: null,
        totalRecords: null,
        sortKey: 'sort_by',
        order: 'order',
    },
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'activity/';
    },
    parseState: function (response) {
        return {totalRecords: response.count};
    },
    parseRecords: function (response) {
        return response.entries;
    },
});

window.System = Backbone.Model.extend({
    initialize: function (attributes, options) {
        this.url = options.url;
        this.command_queue = new CommandQueue([], {system: this});
        this.activity = new SystemActivity([], {system: this});
        // if the system object changes, chances are there are new activity 
        // records describing the change so we refresh activity
        this.on('change', function () { this.activity.fetch(); });
    },
    parse: function (data) {
        data['owner'] = !_.isEmpty(data['owner']) ? new User(data['owner']) : null;
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        data['current_loan'] = (!_.isEmpty(data['current_loan']) ?
                new Loan(data['current_loan'], {parse: true}) : null);
        data['current_reservation'] = (!_.isEmpty(data['current_reservation']) ?
                new Reservation(data['current_reservation'], {parse: true}) : null);
        data['previous_reservation'] = (!_.isEmpty(data['previous_reservation']) ?
                new Reservation(data['previous_reservation'], {parse: true}) : null);
        data['access_policy'] = new AccessPolicy(data['access_policy'],
                {parse: true, system: this});
        data['reprovision_distro_tree'] = (!_.isEmpty(data['reprovision_distro_tree']) ?
                new DistroTree(data['reprovision_distro_tree'], {parse: true}) : null);
        return data;
    },
    add_cc: function (cc, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'cc/' + encodeURIComponent(cc),
            type: 'PUT',
            dataType: 'json',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
                // response body should have the new list of CC
                model.set(data);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    remove_cc: function (cc, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'cc/' + encodeURIComponent(cc),
            type: 'DELETE',
            dataType: 'json',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
                // response body should have the new list of CC
                model.set(data);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    take: function (options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'reservations/',
            type: 'POST',
            //contentType: 'application/json',
            //data: '{}',
            dataType: 'json',
            success: function (data, status, jqxhr) {
                // We refresh the entire system since the user has changed. 
                // Don't invoke the success/error callbacks until the refresh 
                // is complete.
                // This would not be necessary if the system included 
                // reservation data instead of just a 'user' attribute...
                model.fetch({success: options.success, error: options.error});
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    'return': function (options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'reservations/+current',
            type: 'PATCH',
            contentType: 'application/json',
            data: JSON.stringify({finish_time: 'now'}),
            dataType: 'json',
            success: function (data, status, jqxhr) {
                // We refresh the entire system since the user has changed. 
                // Don't invoke the success/error callbacks until the refresh 
                // is complete.
                // This would not be necessary if the system included 
                // reservation data instead of just a 'user' attribute...
                model.fetch({success: options.success, error: options.error});
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    borrow: function (options) {
        this.lend(window.beaker_current_user.get('user_name'), null, options);
    },
    lend: function (recipient, comment, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'loans/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                recipient: {user_name: recipient},
                comment: comment || null,
            }),
            dataType: 'json',
            success: function (data, status, jqxhr) {
                // We refresh the entire system since permissions are likely to 
                // have changed. Don't invoke the success/error callbacks until 
                // the refresh is complete.
                model.fetch({success: options.success, error: options.error});
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    return_loan: function (options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'loans/+current',
            type: 'PATCH',
            contentType: 'application/json',
            data: JSON.stringify({finish: 'now'}),
            dataType: 'json',
            success: function (data, status, jqxhr) {
                // We refresh the entire system since permissions are likely to 
                // have changed. Don't invoke the success/error callbacks until 
                // the refresh is complete.
                model.fetch({success: options.success, error: options.error});
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    request_loan: function (message, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'loan-requests/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                message: message || null,
            }),
            dataType: 'text',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    report_problem: function (message, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'problem-reports/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                message: message || null,
            }),
            dataType: 'text',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    provision: function (options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'installations/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                distro_tree: {id: options.distro_tree_id},
                ks_meta: options.ks_meta,
                koptions: options.koptions,
                koptions_post: options.koptions_post,
                reboot: options.reboot,
            }),
            // This should be dataType: 'json' in future when we return actual 
            // installation data from this call... for now all we get is the 
            // word 'Provisioned'
            dataType: 'text',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    // call this instead of calling .get('access_policy').save() directly, so 
    // that the system attributes can be refreshed
    save_access_policy: function (options) {
        var model = this;
        options = options || {};
        this.get('access_policy').save({}, {
            success: function (data, status, jqxhr) {
                // We refresh the entire system since permissions are likely to 
                // have changed. Don't invoke the success/error callbacks until 
                // the refresh is complete.
                model.fetch({success: options.success, error: options.error});
            },
            error: options.error,
        });
    },
});

})();
