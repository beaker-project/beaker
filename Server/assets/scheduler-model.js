
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.Job = Backbone.Model.extend({
    url: function () {
        // XXX this should not be hardcoded here...
        return window.beaker_url_prefix + 'jobs/' + this.get('id');
    },
    initialize: function (attributes, options) {
        options = options || {};
        if (options.url)
            this.url = options.url;
        var activity = this.activity = new JobActivity([], {job: this});
        // If the Job changes, chances are there are new activity 
        // records describing the change so we refresh activity.
        var update_activity = _.debounce(function () { activity.fetch(); }, 500);
        this.on('change cancelled', update_activity);
        _.each(this.get('recipesets'), function (recipeset) {
            recipeset.on('change cancelled', update_activity);
        });
    },
    toHTML: function () {
        return JST['job-toHTML'](this.attributes).trim();
    },
    parse: function (data) {
        var job = this;
        if (!_.isEmpty(data['owner'])) {
            if (this.get('owner')) {
                var owner = this.get('owner');
                owner.set(owner.parse(data['owner']));
                data['owner'] = owner;
            } else {
                data['owner'] = new User(data['owner'], {parse: true});
            }
        }
        if (!_.isEmpty(data['submitter'])) {
            if (this.get('submitter')) {
                var submitter = this.get('submitter');
                submitter.set(submitter.parse(data['submitter']));
                data['submitter'] = submitter;
            } else {
                data['submitter'] = new User(data['submitter'], {parse: true});
            }
        }
        if (!_.isEmpty(data['group'])) {
            if (this.get('group')) {
                var group = this.get('group') || new Group();
                group.set(group.parse(data['group']));
                data['group'] = group;
            } else {
                data['group'] = new Group(data['group'], {parse: true});
            }
        }
        if (!_.isEmpty(data['recipesets'])) {
            var recipesets = this.get('recipesets') || [];
            data['recipesets'] = _.map(data['recipesets'], function (rsdata, i) {
                var recipeset = recipesets[i];
                if (recipeset) {
                    recipeset.set(recipeset.parse(rsdata));
                } else {
                    recipeset = new RecipeSet(rsdata, {parse: true});
                }
                recipeset.set({job: job}, {silent: true});
                return recipeset;
            });
        }
        if (data['submitted_time']) {
            var parsed = moment.utc(data['submitted_time']);
            data['submitted_time'] = parsed.isSame(this.get('submitted_time')) ? this.get('submitted_time') : parsed;
        }
        return data;
    },
    all_recipes: function () {
        return _.flatten(_.map(this.get('recipesets'), function (rs) {
            return _.map(rs.get('machine_recipes'), function (r) {
                return [r].concat(r.get('guest_recipes') || []);
            });
        }));
    },
    cancel: function (msg) {
        // Note that when cancelling, the overall job status will not change 
        // until beakerd's update_dirty_jobs thread runs. So there will be no 
        // visible attribute changes on our Backbone model straight away.
        // We fire 'cancelling' when the cancellation starts and 'cancelled' 
        // when the server request is complete.
        this.trigger('cancelling');
        _.each(this.get('recipesets'), function (rs) { rs.trigger('cancelling'); });
        var model = this;
        return $.ajax({
            url: this.url + '/status',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'status': 'Cancelled', 'msg': msg}),
        }).done(function () {
            model.trigger('cancelled');
            _.each(model.get('recipesets'), function (rs) { rs.trigger('cancelled'); });
        });
    },
});

window.RecipeSet = Backbone.Model.extend({
    url: function () {
        // XXX this should not be hardcoded here...
        return window.beaker_url_prefix + 'recipesets/' + this.get('id');
    },
    parse: function (data) {
        var recipeset = this;
        if (!_.isEmpty(data['job'])) {
            if (this.get('job')) {
                var job = this.get('job') || new Job();
                job.set(job.parse(data['job']));
                data['job'] = job;
            } else {
                data['job'] = new Job(data['job'], {parse: true});
            }
        }
        if (!_.isEmpty(data['machine_recipes'])) {
            var recipes = this.get('machine_recipes') || [];
            data['machine_recipes'] = _.map(data['machine_recipes'], function (recipedata, i) {
                var recipe = recipes[i];
                if (recipe) {
                    recipe.set(recipe.parse(recipedata));
                } else {
                    recipe = new Recipe(recipedata, {parse: true});
                }
                recipe.set({recipeset: recipeset}, {silent: true});
                return recipe;
            });
        }
        if (data['comments']) {
            var comments = this.get('comments') || new RecipeSetComments([], {recipeset: this});
            comments.reset(data['comments'], {parse: true});
            data['comments'] = comments;
        }
        if (data['queue_time']) {
            var parsed = moment.utc(data['queue_time']);
            data['queue_time'] = parsed.isSame(this.get('queue_time')) ? this.get('queue_time') : parsed;
        }
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- job.get("id") %>#set<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    cancel: function (msg) {
        // Note that when cancelling, the overall job status will not change 
        // until beakerd's update_dirty_jobs thread runs. So there will be no 
        // visible attribute changes on our Backbone model straight away.
        // We fire 'cancelling' when the cancellation starts and 'cancelled' 
        // when the server request is complete.
        this.trigger('cancelling');
        var model = this;
        return $.ajax({
            url: _.result(this, 'url') + '/status',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'status': 'Cancelled', 'msg': msg}),
        }).done(function () { model.trigger('cancelled'); });
    },
    waive: function (comment) {
        var model = this;
        if (!_.isEmpty(comment)) {
            var new_comment = model.get('comments').add({comment: comment});
            return new_comment.save().then(function () {
                return model.save({waived: true}, {patch: true, wait: true});
            });
        } else {
            return model.save({waived: true}, {patch: true, wait: true});
        }
    },
});

window.Recipe = Backbone.Model.extend({
    url: function () {
        // XXX this should not be hardcoded here...
        return window.beaker_url_prefix + 'recipes/' + this.get('id');
    },
    initialize: function (attributes, options) {
        options = options || {};
        if (options.url)
            this.url = options.url;
        // set watchdog timer
        var interval = 1;
        var timer = window.setInterval(function() {
            if (this.get('time_remaining_seconds') > 0) {
                this.set({time_remaining_seconds: this.get('time_remaining_seconds') - 1});
            }
            else {
                window.clearInterval(timer);
            }
        }.bind(this), interval*1000);
    },
    _create_resource: function (data) {
        switch (data['type']) {
            case 'virt':
                resource = new VirtResource(data, {parse: true});
                break;
            case 'guest':
                resource = new GuestResource(data, {parse: true});
                break;
            default:
                resource = new SystemResource(data, {parse: true});
        }
        return resource;
    },
    parse: function (data) {
        var recipe = this;
        if (!_.isEmpty(data['recipeset'])) {
            if (this.get('recipeset')) {
                var recipeset = this.get('recipeset');
                recipeset.set(recipeset.parse(data['recipeset']));
                data['recipeset'] = recipeset;
            } else {
                data['recipeset'] = new RecipeSet(data['recipeset'], {parse: true});
            }
        }
        if (!_.isEmpty(data['hostrecipe'])) {
            if (this.get('hostrecipe')) {
                var hostrecipe = this.get('hostrecipe');
                hostrecipe.set(hostrecipe.parse(data['hostrecipe']));
                data['hostrecipe'] = hostrecipe;
            } else {
                data['hostrecipe'] = new Recipe(data['hostrecipe'], {parse: true});
            }
        }
        if (!_.isEmpty(data['guest_recipes'])) {
            var recipes = this.get('guest_recipes') || [];
            data['guest_recipes'] = _.map(data['guest_recipes'], function (recipedata, i) {
                var recipe = recipes[i];
                if (recipe) {
                    recipe.set(recipe.parse(recipedata));
                } else {
                    recipe = new Recipe(recipedata, {parse: true});
                }
                recipe.set({hostrecipe: recipe}, {silent: true});
                return recipe;
            });
        }
        if (!_.isEmpty(data['distro_tree'])) {
            if (this.get('distro_tree')) {
                var distro_tree = this.get('distro_tree') || new DistroTree();
                distro_tree.set(distro_tree.parse(data['distro_tree']));
                data['distro_tree'] = distro_tree;
            } else {
                data['distro_tree'] = new DistroTree(data['distro_tree'], {parse: true});
            }
        }
        if (!_.isEmpty(data['resource'])) {
            if (this.get('resource')) {
                var resource = this.get('resource');
                resource.set(resource.parse(data['resource']));
                data['resource'] = resource;
            } else {
                data['resource'] = this._create_resource(data['resource']);
            }
        }
        if (!_.isEmpty(data['installation'])) {
            if (this.get('installation')) {
                var installation = this.get('installation') || new Installation();
                installation.set(installation.parse(data['installation']));
                data['installation'] = installation;
            } else {
                data['installation'] = new Installation(data['installation'], {parse: true});
            }
        }
        if (!_.isEmpty(data['tasks'])) {
            var tasks = this.get('tasks') || [];
            data['tasks'] = _.map(data['tasks'], function (taskdata, i) {
                var task = tasks[i];
                if (task) {
                    task.set(task.parse(taskdata));
                } else {
                    task = new RecipeTask(taskdata, {parse: true});
                }
                task.set({recipe: recipe}, {silent: true});
                return task;
            });
        }
        if (!_.isEmpty(data['reservation_request'])) {
            if (this.get('reservation_request')) {
                var reservation_request = this.get('reservation_request') ||
                    new RecipeReservationRequest();
                reservation_request.set(data['reservation_request']);
                data['reservation_request'] = reservation_request;
            } else {
                data['reservation_request'] = new RecipeReservationRequest(
                    data['reservation_request'],
                    {recipe: this});
            }
        }
        if (!_.isEmpty(data['reservation_held_by_recipes'])) {
            data['reservation_held_by_recipes'] = _.map(
                data['reservation_held_by_recipes'], function (recipedata, i) {
                    return new Recipe(recipedata, {parse: true});
                });
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
    toHTML: function () {
        return JST['recipe-toHTML'](this.attributes).trim();
    },
    update_reservation: function (kill_time) {
        var model = this;
        return $.ajax({
            url: this.url + '/watchdog',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({'kill_time': parseInt(kill_time)}),
            dataType: 'json'
        }).then(function () {
            return model.fetch(); // refresh recipe
        });
    },
    get_last_result_started: function() {
        // Get the started time of the last task result of a recipe was never started.
        if (this.get('is_finished') && !this.get('start_time')) {
            var last_task = _.last(this.get('tasks'));
            var last_task_result = last_task ? _.last(last_task.get('results'))
                    : '';
            if (last_task_result)
                return last_task_result.get('start_time');
        }
    },
});

window.RecipeTask = Backbone.Model.extend({
    url: function () {
        // XXX this should not be hardcoded here...
        return _.result(this.get('recipe'), 'url') + '/tasks/' + this.get('id');
    },
    parse: function (data) {
        var recipe_task = this;
        if (!_.isEmpty(data['task'])) {
            if (this.get('task')) {
                var task = this.get('task') || new Task();
                task.set(task.parse(data['task']));
                data['task'] = task;
            } else {
                data['task'] = new Task(data['task'], {parse: true});
            }
        }
        // distro_tree should actually be obtained from Recipe, it's not an 
        // attribute of RecipeTask, this is just here because the system 
        // executed tasks view needed it...
        if (!_.isEmpty(data['distro_tree'])) {
            if (this.get('distro_tree')) {
                var distro_tree = this.get('distro_tree') || new DistroTree();
                distro_tree.set(distro_tree.parse(data['distro_tree']));
                data['distro_tree'] = distro_tree;
            } else {
                data['distro_tree'] = new DistroTree(data['distro_tree'], {parse: true});
            }
        }
        if (!_.isEmpty(data['results'])) {
            var results = this.get('results') || [];
            data['results'] = _.map(data['results'], function (resultdata, i) {
                var result = results[i];
                if (result) {
                    result.set(result.parse(resultdata));
                } else {
                    result = new RecipeTaskResult(resultdata, {parse: true});
                }
                result.set({recipe_task: recipe_task}, {silent: true});
                return result;
            });
        }
        if (data['comments']) {
            var comments = this.get('comments') ||new RecipeTaskComments([], {recipetask: this});
            comments.reset(data['comments'], {parse: true});
            data['comments'] = comments;
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

window.RecipeTaskResult = Backbone.Model.extend({
    url: function () {
        // XXX this should not be hardcoded here...
        return _.result(this.get('recipe_task'), 'url') + '/results/' + this.get('id');
    },
    parse: function (data) {
        var recipe_task_result = this;
        if (data['comments']) {
            var comments = this.get('comments') ||new RecipeTaskResultComments([],
                {recipe_task_result: this});
            comments.reset(data['comments'], {parse: true});
            data['comments'] = comments;
        }
        if (data['start_time']) {
            var parsed = moment.utc(data['start_time']);
            data['start_time'] = parsed.isSame(this.get('start_time')) ? this.get('start_time') : parsed;
        }
        return data;
    },
});

window.SystemResource = Backbone.Model.extend({
    parse: function (data) {
        data['system'] = !_.isEmpty(data['system']) ? new System(data['system']) : null;
        return data;
    },
    resource_summary_fragment: function () {
        return '<span class="fqdn"></span>';
    }
});

window.VirtResource = Backbone.Model.extend({
    parse: function (data) {
        if (!_.isEmpty(data['instance_created'])) {
            var parsed = moment.utc(data['instance_created']);
            data['instance_created'] = parsed.isSame(this.get('instance_created')) ? this.get('instance_created') : parsed;
        }
        return data;
    },
    resource_summary_fragment: function () {
        var result = _.template('OpenStack instance <%= link %>',
                                {link: this.render_link_by_state(this.get('instance_id'),
                                                                 this.get('href'),
                                                                 this.os_instance_present())});
        if (!_.isEmpty(this.get('fqdn'))) {
            result = _.template('<span class="fqdn"></span><br /> (<%= os_instance %>)',
                                {os_instance: result}
                               );
        }
        return result;
    },
    render_link_by_state: function(content, href, show_link) {
        if (show_link) {
            var link = _.template('<a href="<%= href %>"><%= content %></a>');
            return link({content: content, href: href});
        }
        return content;
    },
    os_instance_present: function() {
        return _.isEmpty(this.get('instance_deleted'));
    }
});

window.GuestResource = Backbone.Model.extend({
    resource_summary_fragment: function () {
        return '<span class="fqdn"></span>';
    }
})

window.RecipeReservationRequest = Backbone.Model.extend({
    initialize: function (attributes, options) {
        this.recipe = options.recipe;
        // ensure the 'reserve' attribute is filled in
        if (!_.has(attributes, 'reserve')) {
            this.set('reserve', (attributes['id'] != null));
        }
    },
    url: function () {
        return _.result(this.recipe, 'url') + '/reservation-request';
    },
    // Set model.isNew() to always return False as we want to send a `PATCH` request
    // to the server all the time when saving the model.
    isNew: function () {
        return false;
    }
});

window.JobActivity = Backbone.Collection.extend({
    model: ActivityEntry,
    initialize: function (attributes, options) {
        this.job = options.job;
    },
    url: function () {
        return _.result(this.job, 'url') + '/activity/';
    },
    parse: function (data) {
        return data['entries'];
    },
});

var Comment = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

var RecipeSetComments = Backbone.Collection.extend({
    model: Comment,
    initialize: function (attributes, options) {
        this.recipeset = options.recipeset;
    },
    url: function () {
        return _.result(this.recipeset, 'url') + '/comments/';
    },
});

var RecipeTaskComments = Backbone.Collection.extend({
    model: Comment,
    initialize: function (attributes, options) {
        this.recipetask = options.recipetask;
    },
    url: function () {
        return _.result(this.recipetask, 'url') + '/comments/';
    },
});

var RecipeTaskResultComments = Backbone.Collection.extend({
    model: Comment,
    initialize: function (attributes, options) {
        this.recipe_task_result = options.recipe_task_result;
    },
    url: function () {
        return _.result(this.recipe_task_result, 'url') + '/comments/';
    },
});

})();
