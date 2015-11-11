
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.Job = Backbone.Model.extend({
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
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
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
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- job.get("id") %>"><%- t_id %></a>'),
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
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>recipes/<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
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

})();
