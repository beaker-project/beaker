
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeTasksView = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    expand_recipetask: function(task_id) {
        this.$('.recipe-task')
            .filter('#task' + task_id)
            .find('.collapse')
            .addClass('in')
            .css('height', 'auto')
            .trigger('shown');
    },
    render: function () {
        var $el = this.$el;
        var model= this.model;
        $el.empty().append(new RecipeTasksSummary({model: model}).render().el);
        var is_finished = _.every(model.get('tasks'), function(task) {
                return task.get('is_finished') == true; }) ? true : false;
        var all_collapsed = true;
        var expand_task_id;
        _.each(model.get('tasks'), function (task) {
            var recipe_task = $('<div/>', {"class": "recipe-task",
                    "id": "task" + task.id});
            var task_summary = new RecipeTaskSummary({model: task,
                recipe_start_time: model.get('start_time')}).render().el;
            var task_details = new RecipeTaskDetails({model: task,
                recipe_start_time: model.get('start_time')}).render().el;
            recipe_task.append(task_summary).append(task_details);
            var status = task.get('status');
            var result = task.get('result');
            var expand = false;
            // expand the currently running task if the recipe is not finished.
            if (is_finished) {
                // expand the first failed task
                if ((result == 'Warn' || result == 'Fail' || result == 'Panic') &&
                    all_collapsed) {
                    expand_task_id = task.get('id');
                    all_collapsed = false;
                }
            } else {
                // expand the currently running task
                if (status == 'Running') {
                    expand_task_id = task.get('id');
                }
            }
            $el.append(recipe_task);
        });
        if(expand_task_id) {
            this.expand_recipetask(expand_task_id);
        }
    }
});

var RecipeTasksSummary = Backbone.View.extend({
    template: JST['recipe-tasks-summary'],
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
    initialize: function (options) {
        this.recipe_start_time = options.recipe_start_time;
    },
    render: function () {
        var start_time_diff = get_time_difference(this.model.get('start_time'),
            this.recipe_start_time);
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
        'hidden.bs.collapse': 'toggle_task_details',
        'shown.bs.collapse': 'toggle_task_details',
        'click .toggle-results-settings button': 'toggle_results_settings'
    },
    toggle_task_details: function(e) {
        var id = this.model.id;
        switch (e.type) {
            case 'shown':
                $('#recipe-task-icon-' + id).find("i")
                        .removeClass("fa-caret-right").addClass("fa-caret-down");
                break;
            case 'hidden':
                $('#recipe-task-icon-' + id).find("i")
                        .removeClass("fa-caret-down").addClass("fa-caret-right");
                break;
        }
    },
    toggle_results_settings: function (evt) {
        var selected_side;
        if (!_.isEmpty(evt)) {
            evt.preventDefault();
            selected_side = $(evt.currentTarget).text() ;
        } else {
            selected_side = 'Results';
        }
        switch (selected_side) {
            case 'Results':
                this.$('.recipe-task-results').show();
                this.$('.recipe-task-settings').hide();
                break;
            case 'Settings':
                this.$('.recipe-task-results').hide();
                this.$('.recipe-task-settings').show();
                break;
        }
    },
    initialize: function (options) {
        this.recipe_start_time = options.recipe_start_time;
    },
    render: function () {
        var model = this.model;
        var $el = this.$el;
        $el.html(this.template(model.attributes));
        var recipe_start_time = this.recipe_start_time;
        this.$(".recipe-task-results-settings").empty()
            .append(new RecipeTaskResults({model: this.model,
                recipe_start_time: this.recipe_start_time}).el)
            .append(new RecipeTaskSettings({model: this.model}).el);
        this.toggle_results_settings();
        return this;
    },
});

var RecipeTaskResults = Backbone.View.extend({
    className: 'recipe-task-results',
    template: JST['recipe-task-results'],
    initialize: function (options) {
        this.recipe_start_time = options.recipe_start_time;
        this.render();
    },
    render: function () {
        this.$el.empty();
        if (_.isEmpty(this.model.get('results'))) {
            this.$el.text('No results reported for this task.');
        } else {
            var $el = this.$el;
            var recipe_start_time = this.recipe_start_time;
            _.each(this.model.get('results'), function (result) {
                $el.append(new RecipeTaskResultView({model: result,
                    recipe_start_time: recipe_start_time}).render().el);
            });
        }
        return this;
    }
});

var RecipeTaskResultView = Backbone.View.extend({
    template: JST['recipe-task-result'],
    className: 'recipe-task-result',
    initialize: function (options) {
        this.recipe_start_time = options.recipe_start_time;
    },
    render: function () {
        var start_time_diff = get_time_difference(this.model.get('start_time'),
            this.recipe_start_time);
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
