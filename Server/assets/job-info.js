
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.JobInfoView = Backbone.View.extend({
    tagName: 'div',
    className: 'job-info',
    events: {
        'click a.activity': 'show_activity',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        new JobSummaryView({model: this.model}).$el
            .appendTo(this.$el);
        new JobWhiteboardView({model: this.model}).$el
            .appendTo(this.$el);
    },
    show_activity: function (evt) {
        evt.preventDefault();
        new JobActivityModal({model: this.model});
    },
});

var JobWhiteboardView = Backbone.View.extend({
    tagName: 'div',
    className: 'job-whiteboard',
    template: JST['job-whiteboard'],
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

var JobSummaryView = Backbone.View.extend({
    tagName: 'div',
    className: 'job-summary',
    template: JST['job-summary'],
    initialize: function () {
        // XXX listen to individual recipes' change events?
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        var recipe_count = _.size(this.model.all_recipes());
        var finished_recipe_count = _.size(_.filter(this.model.all_recipes(),
                function (r) { return r.get('is_finished'); }));
        var template_data = _.extend({
            recipe_count: recipe_count,
            finished_recipe_count: finished_recipe_count,
        }, this.model.attributes);
        this.$el.html(this.template(template_data));
    },
});

// The job page itself will also trigger this if the #activity anchor exists on 
// page load.
window.JobActivityModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal job-activity',
    template: JST['job-activity'],
    events: {
        'hidden': 'hidden',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        window.history.replaceState(undefined, undefined, '#activity');
        this.$('button:first').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('.modal-body').append(new JobActivityGrid({model: this.model}).el);
    },
    hidden: function () {
        // get rid of the #activity anchor
        window.history.replaceState(undefined, undefined,
                window.location.pathname + window.location.search);
        this.remove();
    },
});

var JobActivityObjectCell = Backgrid.Cell.extend({
    render: function () {
        this.$el.text(this.model.get(this.column.get('name')).get('t_id'));
        return this;
    },
});

var JobActivityGrid = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model.activity;
        options.pageable = false;
        options.filterable = false;
        options.columns = [
            {name: 'user', label: 'User', cell: BackgridUserCell, editable: false},
            {name: 'service', label: 'Via', cell: 'string', editable: false},
            {name: 'created', label: 'Created', cell: BackgridDateTimeCell, editable: false},
            {name: 'object', label: 'Object', cell: JobActivityObjectCell, editable: false},
            {name: 'field_name', label: 'Property', cell: 'string', editable: false},
            {name: 'action', label: 'Action', cell: 'string', editable: false},
            {name: 'old_value', label: 'Old Value', cell: 'string', editable: false},
            {name: 'new_value', label: 'New Value', cell: 'string', editable: false},
        ];
        options.name = 'job activity';
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

})();
