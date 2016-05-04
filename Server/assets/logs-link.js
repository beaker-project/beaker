// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * Beaker itself doesn't know which of the log files is the most important
 * or interesting for a user, but we can make some guesses based on naming
 * conventions.
 */
window.get_main_log = function(logs) {
    var log = _.find(logs, function(log) {
        var path = log.path;
        if(path.startsWith('anaconda.log') || path.startsWith('TESTOUT') ||
            path.startsWith('test_log') || path == 'taskout.log' ||
            path == 'resultoutputfile.log') {
                return log;
        }
    });
    if (!log) {
        log = logs[0];
    }
    return log;
};

window.LogsLink = Backbone.View.extend({
    template: JST['logs-link'],
    initialize: function () {
        this.listenTo(this.model, 'change:logs', this.render);
        this.render();
    },
    render: function () {
        var all_logs = this.model.get('logs') || [];
        // console.log is treated specially on the page
        all_logs = _.reject(all_logs, function (log) { return log.path == 'console.log'; });
        var main_log = get_main_log(all_logs);
        // filter out the main log
        var other_logs = _.reject(all_logs, function(log){return log.id == main_log.id; });
        this.$el.html(this.template(_.extend({main_log: main_log,
            other_logs: other_logs}, this.model.attributes)));
        this.$('.logs-link').beaker_popover({
            model: this.model,
            view_type: LogsPopover,
        });
        return this;
    },
});

window.LogsPopover = BeakerPopoverView.extend({
    className: 'popover logs-popover',
    render: function () {
        BeakerPopoverView.prototype.render.apply(this);
        new LogsList({model: this.model}).$el
            .appendTo(this.$('.popover-content'));
    },
});

window.LogsList = Backbone.View.extend({
    template: JST['logs-list'],
    initialize: function (options) {
        this.listenTo(this.model, 'change:logs', this.render);
        this.render();
    },
    render: function () {
        var all_logs = this.model.get('logs') || [];
        var main_log = get_main_log(all_logs);
        // filter out the main log
        var other_logs = _.reject(all_logs, function(log){return log.id == main_log.id; });
        // also filter out console.log because that's treated specially on the page
        var other_logs = _.reject(other_logs, function (log) { return log.path == 'console.log'; });
        this.$el.html(this.template({logs: other_logs}));
        return this;
    },
});

})();
