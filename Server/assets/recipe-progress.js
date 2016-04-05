
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeProgressBar = Backbone.View.extend({
    tagName: 'div',
    className: 'recipe-progress',
    initialize: function () {
        this.render();
    },
    render: function () {
        var model = this.model;
        var bar = $('<div class="progress"/>');
        var sumtasks = 0;
        bar.append(_.map([
            ['ntasks', 'bar-default'],
            ['ptasks', 'bar-success'],
            ['wtasks', 'bar-warning'],
            ['ftasks', 'bar-danger'],
            ['ktasks', 'bar-info'],
        ], function (item) {
            var attr = item[0], barstyle = item[1];
            var width = 100.0 * model.get(attr) / model.get('ttasks');
            sumtasks += model.get(attr);
            return $('<div/>')
                .addClass('bar')
                .addClass(barstyle)
                .width(width.toFixed(3) + '%');
        }));
        // For overall progress we want integer truncation, rather than 
        // rounding, so that a very large recipe with only one incomplete task 
        // will always be 99%, not rounded up to 100%.
        var progress = $('<span/>')
            .addClass('progress-text')
            .text('' + Math.floor(100.0 * sumtasks / model.get('ttasks')) + '%');
        this.$el.empty().append(progress).append(bar);
    },
});

})();
