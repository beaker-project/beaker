
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeTasksView = Backbone.View.extend({
    className: 'tab-pane recipe-tasks',
    initialize: function () {
        this.render();
    },
    expand_task_ids: function (ids) {
        // We set the classes and heights directly here, rather than invoking 
        // the Boostrap plugins "properly" by calling .collapse(), so that the 
        // transitions are skipped and no events are fired. We only want that 
        // to happen when a *user* does the expanding, not a script.
        this.$('.recipe-task')
            .has('.collapse.in')
            .filter(function () { return !_.contains(ids, this.dataset.taskId); })
            .find('.task-icon a')
            .addClass('collapsed')
            .end()
            .find('.collapse')
            .removeClass('in')
            .height(0);
        this.$('.recipe-task')
            .filter(function () { return _.contains(ids, this.dataset.taskId); })
            .find('.task-icon a')
            .removeClass('collapsed')
            .end()
            .find('.collapse')
            .addClass('in')
            .height('auto');
    },
    expanded_task_ids: function () {
        var expanded = this.$('.recipe-task').has('.collapse.in');
        return _.map(expanded.get(), function (elem) { return elem.dataset.taskId; });
    },
    render: function () {
        var view = this;
        var model= this.model;
        this.$el.empty()
            .append(new RecipeTasksSummary({model: model}).render().el)
            .append(_.map(model.get('tasks'), function (task) {
                var recipe_task = $('<div/>', {"class": "recipe-task",
                        "id": "task" + task.id, "data-task-id": task.id});
                var task_summary = new RecipeTaskSummary({model: task}).render().el;
                var task_details = new RecipeTaskDetails({model: task}).render().el;
                recipe_task.append(task_summary).append(task_details);
                recipe_task.find('.collapse').on('shown hidden', function () { view.trigger('expand:task'); });
                return recipe_task;
            }));
    }
});

var RecipeTasksSummary = Backbone.View.extend({
    template: JST['recipe-tasks-summary'],
    initialize: function () {
        this.listenTo(this.model, 'change:result', this.render);
        var view = this;
        _.each(this.model.get('tasks'), function (task) {
            view.listenTo(task, 'change:is_finished', view.render);
        });
    },
    render: function () {
        var task_count = _.size(this.model.get('tasks'));
        var finished_task_count = _.size(_.filter(this.model.get('tasks'),
            function (r) { return r.get('is_finished'); }));
        var template_data = _.extend({
                task_count: task_count,
                finished_task_count: finished_task_count,
        }, this.model.attributes);
        this.$el.html(this.template(template_data));
        this.$('.recipe-status').append(new RecipeProgressBar({model: this.model}).el);
        return this;
    },
});

var RecipeTaskSummary = Backbone.View.extend({
    template: JST['recipe-task-summary'],
    className: 'recipe-task-summary',
    events: {
        'click .task-icon a': function (evt) { evt.preventDefault(); },
    },
    initialize: function (options) {
        this.listenTo(this.model, 'change', this.render);
        this.listenTo(this.model.get('recipe'), 'change:start_time', this.render);
    },
    render: function () {
        var start_time_diff = get_time_difference(this.model.get('start_time'),
            this.model.get('recipe').get('start_time'));
        this.$el.html(this.template(_.extend({start_time_diff: start_time_diff},
            this.model.attributes)));
        var status = this.model.get('status');
        var result = this.model.get('result');
        if (status == 'Cancelled' || status == 'Aborted') {
            $('<span/>')
                .addClass('label label-warning')
                .text(status)
                .appendTo(this.$('.recipe-task-status'));
        } else if (status == 'Running') {
            $('<span/>')
                .text(status)
                .appendTo(this.$('.recipe-task-status'));
        } else if (status == 'Completed') {
            $('<span/>')
                .addClass('label label-result-' + result.toLowerCase())
                .text(result)
                .appendTo(this.$('.recipe-task-status'));
        }
        new LogsLink({model: this.model}).$el.appendTo(this.$('div.task-logs'));
        new CommentsLink({model: this.model}).$el.appendTo(this.$('div.task-comments'));
        return this;
    },
});

var RecipeTaskDetails = Backbone.View.extend({
    template: JST['recipe-task-details'],
    className: 'recipe-task-details collapse',
    attributes : function () {
       return {
         id : "recipe-task-details-" + this.model.id
       };
    },
    events: {
        'click .toggle-results-settings button': 'toggle_results_settings'
    },
    toggle_results_settings: function (evt) {
        var selected_side;
        if (!_.isEmpty(evt)) {
            evt.preventDefault();
            selected_side = $(evt.currentTarget).text() ;
        } else {
            selected_side = !this.model.get('recipe').get('is_deleted') ? 'Results' : 'Settings';
        }
        switch (selected_side) {
            case 'Results':
                this.$('.recipe-task-results').show();
                this.$('.recipe-task-settings').hide();
                this.$(".toggle-results-settings button:contains('Results')").addClass("active");
                break;
            case 'Settings':
                this.$('.recipe-task-results').hide();
                this.$('.recipe-task-settings').show();
                this.$(".toggle-results-settings button:contains('Settings')").addClass("active");
                break;
        }
    },
    initialize: function (options) {
        this.listenTo(this.model.get('recipe'), 'change:start_time change:is_deleted', this.render);
    },
    render: function () {
        var model = this.model;
        var is_deleted = model.get('recipe').get('is_deleted');
        this.$el.html(this.template(_.extend({is_deleted: is_deleted}, model.attributes)));
        if (!is_deleted) {
            this.$(".recipe-task-results-settings").append(
                new RecipeTaskResults({model: this.model}).el);
        }
        this.$(".recipe-task-results-settings").append(
            new RecipeTaskSettings({model: this.model}).el);
        this.toggle_results_settings();
        return this;
    },
});

var RecipeTaskResults = Backbone.View.extend({
    className: 'recipe-task-results',
    template: JST['recipe-task-results'],
    initialize: function (options) {
        this.listenTo(this.model, 'change:results', this.render);
        this.render();
    },
    render: function () {
        this.$el.empty();
        if (_.isEmpty(this.model.get('results'))) {
            this.$el.text('No results reported for this task.');
        } else {
            this.$el.append(_.map(this.model.get('results'), function (result) {
                return new RecipeTaskResultView({model: result}).render().el;
            }));
        }
        return this;
    }
});

var RecipeTaskResultView = Backbone.View.extend({
    template: JST['recipe-task-result'],
    className: 'recipe-task-result',
    initialize: function (options) {
        this.listenTo(this.model, 'change', this.render);
        this.listenTo(this.model.get('recipe_task').get('recipe'), 'change:start_time', this.render);
    },
    render: function () {
        var start_time_diff = get_time_difference(this.model.get('start_time'),
            this.model.get('recipe_task').get('recipe').get('start_time'));
        this.$el.html(this.template(_.extend({start_time_diff: start_time_diff},
            this.model.attributes)));
        new LogsLink({model: this.model}).$el.appendTo(this.$('div.task-result-logs'));
        new CommentsLink({model: this.model}).$el.appendTo(this.$('div.task-result-comments'));
        return this;
    },
});

var RecipeTaskSettings = Backbone.View.extend({
    className: 'recipe-task-settings',
    template: JST['recipe-task-settings'],
    initialize: function (options) {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },
});

})();
