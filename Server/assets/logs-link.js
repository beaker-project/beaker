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
    // This view is using DOM methods instead of a JST template for speed, 
    // since it's in the hot path for task results.
    initialize: function () {
        this.listenTo(this.model, 'change:logs', this.render);
        this.render();
    },
    render: function () {
        this.$el.empty();
        var all_logs = this.model.get('logs') || [];
        // console.log is treated specially on the page
        all_logs = _.reject(all_logs, function (log) { return log.path == 'console.log'; });
        if (all_logs.length) {
            var main_log = get_main_log(all_logs);
            var main_log_span = document.createElement('span');
            main_log_span.className = 'main-log';
            var main_log_link = document.createElement('a');
            main_log_link.href = main_log.href;
            var main_log_icon = document.createElement('i');
            main_log_icon.className = 'fa fa-file-o';
            main_log_link.appendChild(main_log_icon);
            main_log_link.appendChild(document.createTextNode(' '));
            main_log_link.appendChild(document.createTextNode(main_log.path));
            main_log_span.appendChild(main_log_link);
            this.el.appendChild(main_log_span);

            var other_logs = _.reject(all_logs, function(log){return log.id == main_log.id; });
            if (other_logs.length) {
                var other_logs_span = document.createElement('span');
                other_logs_span.appendChild(document.createTextNode('+ '));
                var other_logs_link = document.createElement('a');
                other_logs_link.href = '#';
                other_logs_link.className = 'logs-link';
                other_logs_link.appendChild(document.createTextNode(other_logs.length.toString()));
                other_logs_link.appendChild(document.createTextNode(' '));
                var more_logs_icon = document.createElement('i');
                more_logs_icon.className = 'fa fa-files-o';
                more_logs_icon_arialabel = document.createAttribute('aria-label');
                more_logs_icon_arialabel.value = 'more logs';
                more_logs_icon.setAttributeNode(more_logs_icon_arialabel);
                other_logs_link.appendChild(more_logs_icon);
                other_logs_span.appendChild(other_logs_link);
                this.el.appendChild(document.createTextNode(' '));
                this.el.appendChild(other_logs_span);
                $(other_logs_link).beaker_popover({
                    model: this.model,
                    view_type: LogsPopover,
                });
            }
        }
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
