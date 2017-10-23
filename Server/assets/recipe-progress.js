
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeProgressBar = Backbone.View.extend({
    tagName: 'div',
    className: 'recipe-progress',
    initialize: function () {
        _.each(this.model.get('tasks'), function (task) {
            this.listenTo(task, 'change', this.render);
        }, this);
        this.render();
    },
    render: function () {
        var model = this.model;
        var tasks = this.model.get('tasks');
        var completed_count = _.filter(tasks,
                function (task) { return task.get('is_finished'); }).length;
        var bar = $('<div class="progress"/>');
        _.each(tasks, function (task) {
            if (!task.get('is_finished'))
                return;
            var chunk = document.createElement('a');
            chunk.href = _.result(model, 'url') + '#task' + task.get('id');
            chunk.title = task.get('name');
            chunk.className = 'bar bar-result-' + task.get('result').toLowerCase();
            var width = 100.0 / tasks.length;
            chunk.style.width = width.toFixed(3) + '%';
            bar.append(chunk);
        });
        // For overall progress we want integer truncation, rather than 
        // rounding, so that a very large recipe with only one incomplete task 
        // will always be 99%, not rounded up to 100%.
        var progress = $('<span/>')
            .addClass('progress-text')
            .text('' + Math.floor(100.0 * completed_count / tasks.length) + '%');
        this.$el.empty().append(progress).append(bar);
    },
});

})();
