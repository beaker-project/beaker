
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeQuickInfoView = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.empty();
        new RecipeSummaryView({model: this.model}).$el
            .appendTo(this.$el);
        new RecipeWhiteBoardView({model: this.model}).$el
            .appendTo(this.$el);
        var status = this.model.get('status');
        if (status != 'New' && status != 'Processed' &&
                status != 'Queued' && status != 'Scheduled') {
            new RecipeRuntimeStatusView({model: this.model}).$el
                .appendTo(this.$el);
        }
    },
});

window.RecipeSummaryView = Backbone.View.extend({
    tagName: 'div',
    className: 'recipe-summary',
    template: JST['recipe-summary'],
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(_.extend({
            last_result_started: this.model.get_last_result_started()},
            this.model.attributes)));
    },
});

window.RecipeWhiteBoardView = Backbone.View.extend({
    tagName: 'div',
    className: 'recipe-whiteboard',
    template: JST['recipe-whiteboard'],
    initialize: function () {
        this.listenTo(this.model, 'change:whiteboard', this.render);
        this.render();
    },
    render: function () {
        var whiteboard = this.model.get('whiteboard');
        var whiteboard_html = '';
        if (whiteboard) {
            var whiteboard_html = marked(this.model.get('whiteboard'),
                    {sanitize: true, smartypants: false});
        }
        this.$el.html(this.template({whiteboard_html: whiteboard_html}));
        return this;
    },
});

window.RecipeRuntimeStatusView = Backbone.View.extend({
    tagName: 'div',
    className: 'recipe-runtime-status',
    template: JST['recipe-runtime-status'],
    initialize: function () {
        this.listenTo(this.model, 'change:time_remaining_seconds', this.render);
        this.render();
    },
    clearTimer: function () {
        window.clearInterval(this.timer);
    },
    render: function () {
        // Clear the existing countdown timer when re-rendering.
        if (this.timer) {
            this.clearTimer();
        }
        var console_log = _.findWhere(this.model.get('logs'), {path: 'console.log'});
        this.$el.html(this.template(_.extend({console_log: console_log}, this.model.attributes)));
        var time_remaining_seconds = this.model.get('time_remaining_seconds');
        if (time_remaining_seconds && time_remaining_seconds > 0) {
            var duration = moment.duration(time_remaining_seconds, 'seconds');
            var interval = 1;
            var model = this.model;
            // Initialize the countdown timer
            this.timer = window.setInterval(function() {
                if (duration.asSeconds() <= 0) {
                    this.clearTimer();
                } else {
                    duration = moment.duration(
                        duration.asSeconds() - interval, 'seconds');
                    $('.recipe-watchdog-countdown').text(
                        duration.format("hh:mm:ss", {trim: false}));
                }
            }.bind(this), interval*1000);
        }
        return this;
    },
});

})();
