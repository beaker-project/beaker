
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

window.SystemAccessPolicy = Backbone.Model.extend({
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
    save_access_policy: function (options) {
        var model = this;
        options = options || {};
        return this.save()
            // We refresh the entire system since permissions are likely to 
            // have changed.
            .then(function () { return model.system.fetch(); })
            .done(function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
            })
            .fail(function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            });
    },
});

window.Command = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        if (data['submitted']) {
            var parsed = moment.utc(data['submitted']);
            data['submitted'] = parsed.isSame(this.get('submitted')) ? this.get('submitted') : parsed;
        }
        if (data['start_time']) {
            var parsed = moment.utc(data['start_time']);
            data['start_time'] = parsed.isSame(this.get('start_time')) ? this.get('start_time') : parsed;
        }
        if (data['finish_time']) {
            var parsed = moment.utc(data['finish_time']);
            data['finish_time'] = parsed.isSame(this.get('finish_time')) ? this.get('finish_time') : parsed;
        }
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

window.SystemActivity = BeakerPageableCollection.extend({
    model: ActivityEntry,
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'activity/';
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

window.SystemPoolAccessPolicy = Backbone.Model.extend({
    initialize: function (attributes, options) {
        this.system_pool = options.system_pool;
    },
    url: function () {
        return _.result(this.system_pool, 'url') + 'access-policy/';
    },
    parse: function (data) {
        data['rules'] = new AccessPolicyRules(data['rules'], {parse: true});
        return data;
    },
    save_access_policy: function (options) {
        var model = this;
        options = options || {};
        return this.save()
            // to refresh the can_edit_policy attribute
            .then(function () { return model.system_pool.fetch(); })
            .done(function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
            })
            .fail(function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            });
    },
});

window.SystemPool = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>pools/<%- encodeURIComponent(name) %>/"><%- name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    initialize: function (attributes, options) {
        if(options.url)
            this.url = options.url;
    },
    parse: function (data) {
        data['owner'] = !_.isEmpty(data['owner'])
                ? (!_.isEmpty(data['owner']['group_name'])
                    ? new Group(data['owner'], {parse: true})
                    : new User(data['owner'], {parse: true}))
                : null;
        data['access_policy'] = new SystemPoolAccessPolicy(data['access_policy'],
                {parse: true, system_pool: this});
        return data;
    },
    add_system: function (system, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'systems/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'fqdn': system}),
            success: function (data, status, jqxhr) {
                model.set({'systems': model.get('systems').concat([system])});
                if (options.success)
                    options.success(model, data, options);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    remove_system: function (system, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'systems/' + '?fqdn=' + encodeURIComponent(system),
            type: 'DELETE',
            contentType: 'application/json',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
                model.set({'systems': _.without(model.get('systems'), system)});
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
});

/* The collection of *all* system pools in Beaker. */
window.SystemPools = BeakerPageableCollection.extend({
    model: SystemPool,
    initialize: function (attributes, options) {
        this.url = options.url;
    },
});

var SystemNote = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

var SystemNotes = Backbone.Collection.extend({
    model: SystemNote,
    initialize: function (attributes, options) {
        this.system = options.system;
    },
    url: function () {
        return _.result(this.system, 'url') + 'notes/';
    },
});

window.System = Backbone.Model.extend({
    initialize: function (attributes, options) {
        options = options || {};
        if(options.url)
            this.url = options.url;
        else
            this.url = window.beaker_url_prefix + 'systems/' + encodeURIComponent(this.get('fqdn')) + '/';

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
        data['access_policy'] = new SystemAccessPolicy(data['access_policy'],
                {parse: true, system: this});
        data['reprovision_distro_tree'] = (!_.isEmpty(data['reprovision_distro_tree']) ?
                new DistroTree(data['reprovision_distro_tree'], {parse: true}) : null);
        if (_.has(data, 'notes')) {
            var notes = this.get('notes') || new SystemNotes([], {system: this});
            notes.reset(data['notes'], {parse: true});
            data['notes'] = notes;
        }
        return data;
    },
    // We build an absolute URL in the hyperlink so that it works properly when 
    // copied to the clipboard and pasted elsewhere.
    _toHTML_template: _.template('<a href="<%- window.location.protocol %>//<%- window.location.host %><%- beaker_url_prefix %>view/<%- encodeURIComponent(fqdn) %>"><%- fqdn %></a>'),
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
        return $.ajax({
            url: beaker_url_prefix + 'pools/' + encodeURIComponent(pool) + '/systems/',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'fqdn': model.get('fqdn')}),
            dataType: 'json',
            success: function (data, status, jqxhr) {
                var can_remove_from_pool = model.get('can_remove_from_pool');
                can_remove_from_pool[pool] = true;
                model.set({'pools': model.get('pools').concat([pool]), 'can_remove_from_pool': can_remove_from_pool});
                if (options.success)
                    options.success(model, data, options);
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
                // Removing a system from a pool can lead to potential change
                // in active_access_policy
                model.fetch();
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
});

})();
