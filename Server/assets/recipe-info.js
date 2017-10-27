
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeQuickInfoView = Backbone.View.extend({
    initialize: function () {
        this.listenTo(this.model, 'change:status', this.render);
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
        this.fqdn_view = new RecipeFqdnView({model: this.model});
        this.listenTo(this.model, 'change:start_time change:finish_time change:resource change:status ' +
        'change:possible_systems', this.render);
        this.render();
    },
    render: function () {
        var data = _.extend({
            last_result_started: this.model.get_last_result_started()}, this.model.attributes);
        this.$el.html(this.template(data));
        this.fqdn_view.setElement(this.$('.fqdn').get(0)).render();
    },
});

window.RecipeFqdnView = Backbone.View.extend({
    tagName: 'span',
    template: JST['recipe-fqdn'],
    events: {
        'click .copy-hostname': 'copy_hostname',
        'click .report-problem': 'sys_report_problem',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:resource', this.render);
    },
    render: function () {
        this.$el.empty().addClass('btn-group btn-group-inline');
        var resource = this.model.get('resource');
        if (_.isEmpty(resource))
            return;
        var fqdn = resource.get('fqdn');
        if (_.isEmpty(fqdn))
            return;
        if (fqdn.endsWith('.openstacklocal')) {
            fqdn = resource.get('floating_ip');
        }
        this.$el.html(this.template(_.extend(
                resource.attributes,
                {fqdn: fqdn, recipe_status: this.model.get('status')})));
    },
    copy_hostname: function (evt) {
        evt.preventDefault();
        var resource = this.model.get('resource');
        if (_.isEmpty(resource))
            return;
        var hostname = resource.get('fqdn');
        var html = (!_.isEmpty(resource.get('system')))
                 ? resource.get('system').toHTML() : null;
        $(document).one('copy', function (evt) {
            evt.preventDefault();
            evt.originalEvent.clipboardData.setData('text/plain', hostname);
            if (html)
                evt.originalEvent.clipboardData.setData('text/html', html);
        });
        document.execCommand('copy');
    },
    sys_report_problem: function (evt) {
        system = this.model.get('resource').get('system')
        new SystemReportProblemModal({model: system});
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
        this.listenTo(this.model, 'change:logs', this.render);
        this.render();
    },
    render: function () {
        var console_log = _.findWhere(this.model.get('logs'), {path: 'console.log'});
        this.$el.html(this.template(_.extend({console_log: console_log}, this.model.attributes)));
        new RecipeWatchdogTimeRemainingView({model: this.model}).$el
                .appendTo(this.$el);
        return this;
    },
});

window.RecipeWatchdogTimeRemainingView = Backbone.View.extend({
    tagName: 'p',
    className: 'recipe-watchdog-time-remaining',
    initialize: function() {
        this.listenTo(this.model, 'change:time_remaining_seconds', this.render);
        this.render();
    },
    render: function() {
        var time_remaining_seconds = this.model.get('time_remaining_seconds');
        if (!_.isNull(time_remaining_seconds)) {
            var duration = moment.duration(time_remaining_seconds, 'seconds');
            this.$el.text(
                "Remaining watchdog time: " + duration.format("hh:mm:ss", {trim: false}));
        }
        else {
            this.$el.empty();
        }
        return this;
    }
})

})();
