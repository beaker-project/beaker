
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * System-related models for client-side Backbone widgets.
 */

window.Loan = Backbone.Model.extend({
    parse: function (data) {
        data['recipient_user'] = !_.isEmpty(data['recipient_user']) ? new User(data['recipient_user']) : null;
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
        data['rules'] = new AccessPolicyRules(data['rules'], {parse: true});
        return data;
    },
});

window.Command = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

window.CommandQueue = BeakerPageableCollection.extend({
    model: Command,
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'commands/';
    },
});

window.SystemActivityEntry = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

window.SystemActivity = BeakerPageableCollection.extend({
    model: SystemActivityEntry,
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'activity/';
    },
});

window.Task = Backbone.Model.extend({});

window.RecipeTask = Backbone.Model.extend({
    parse: function (data) {
        data['task'] = !_.isEmpty(data['task']) ? new Task(data['task']) : null;
        data['distro_tree'] = !_.isEmpty(data['distro_tree']) ? new DistroTree(data['distro_tree'], {parse: true}) : null;
        return data;
    },
});

window.SystemExecutedTasks = BeakerPageableCollection.extend({
    model: RecipeTask,
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'executed-tasks/';
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
        this.executed_tasks = new SystemExecutedTasks([], {system: this});
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
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>view/<%- encodeURIComponent(fqdn) %>"><%- fqdn %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
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

    add_to_pool: function (pool, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: beaker_url_prefix + 'pools/' + encodeURIComponent(pool) + '/systems/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'fqdn': model.get('fqdn')}),
            dataType: 'json',
            success: function (data, status, jqxhr) {
                var can_remove_from_pool = model.get('can_remove_from_pool');
                can_remove_from_pool[pool] = true;
                model.set({'pools': model.get('pools').concat([pool]), 'can_remove_from_pool': can_remove_from_pool});
                if (!(_.contains(model.get('all_pools'), pool))) {
                    model.set('all_pools', model.get('all_pools').concat([pool]));
                }
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },

    remove_from_pool: function (pool, options) {
        var model = this
        options = options || {};
        $.ajax({
            url: beaker_url_prefix + 'pools/' + encodeURIComponent(pool) +
                '/systems/' + '?fqdn=' + encodeURIComponent(model.get('fqdn')),
            type: 'DELETE',
            contentType: 'application/json',
            success: function (data, status, jqxhr) {
                var pools = model.get('pools');
                var pool_index = _.indexOf(pools, pool);
                pools.splice(pool_index, 1);
                model.set('pools', pools);
                // XXX: better way?
                model.trigger('change');
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
    command: function (action, options) {
        var model = this;
        options = options || {};
        if (action == 'reboot') {
            // reboot is a special case, it is actually two commands: off then on
            var off = new Command({action: 'off'}, {collection: this.command_queue});
            var on = new Command({action: 'on'}, {collection: this.command_queue});
            off.save()
                .fail(function (jqxhr, status, error) {
                    if (options.error)
                        options.error(model, jqxhr, options);
                    })
                .done(function () {
                    on.save()
                        .always(function () { model.command_queue.fetch(); })
                        .done(function (data, status, jqxhr) {
                            if (options.success)
                                options.success(model, data, options);
                            })
                        .fail(function (jqxhr, status, error) {
                            if (options.error)
                                options.error(model, jqxhr, options);
                            });
                });
        } else {
            var command = new Command({action: action}, {collection: this.command_queue});
            command.save()
                .done(function () { model.command_queue.fetch(); })
                .done(function (data, status, jqxhr) {
                    if (options.success)
                        options.success(model, data, options);
                    })
                .fail(function (jqxhr, status, error) {
                    if (options.error)
                        options.error(model, jqxhr, options);
                    });
        }
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
