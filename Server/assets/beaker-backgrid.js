
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/* Extra Beaker-specific stuff for Backgrid */

;(function () {

window.BackgridUserCell = Backgrid.Cell.extend({
    template: JST['backgrid-user-cell'],
    className: 'user-cell',
    formatter: {
        fromRaw: function (value) {
            if (_.isEmpty(value))
                return '';
            return value.get('user_name');
        },
        toRaw: function (value) {
            if (_.isEmpty(value))
                return null;
            return new User({user_name: value});
        },
    },
    render: function () {
        this.$el.empty();
        var user = this.model.get(this.column.get('name'));
        if (!_.isEmpty(user)) {
            this.$el.html(this.template(user.attributes));
        }
        return this;
    },
});

// Based on https://github.com/wyuenho/backgrid-moment-cell/blob/master/backgrid-moment-cell.js
// but simplified for Beaker's specific needs
window.BackgridDateTimeCell = Backgrid.Cell.extend({
    className: 'datetime-cell',
    formatter: {
        fromRaw: function (value) {
            if (!value)
                return '';
            return moment.utc(value).local().format('YYYY-MM-DD HH:mm:ss Z');
        },
        toRaw: function (value) {
            return value;
        },
    },
});

var BeakerBackgridFilter = Backbone.View.extend({
    tagName: 'form',
    className: 'grid-filter form-search',
    template: JST['backgrid-filter'],
    events: {
        'submit': 'submit',
        'keypress input': 'maybe_changed',
        'change input': 'maybe_changed',
        'input input': 'maybe_changed',
        'click .trigger-query-builder': 'show_query_builder',
    },
    initialize: function (options) {
        this.columns = options.columns;
        this.collection.queryParams['q'] = _.bind(this.val, this);
    },
    render: function () {
        this.$el.html(this.template());
        return this;
    },
    val: function () {
        if (arguments.length) {
            this.$('input').val(arguments[0]);
            this.maybe_changed();
        } else {
            return this.$('input').val();
        }
    },
    submit: function (evt) {
        this.last_val = this.val();
        this.collection.getFirstPage();
        if (evt) evt.preventDefault();
    },
    maybe_changed: _.debounce(function () {
        if (this.val() != this.last_val)
            this.submit();
    }, 500 /* ms */),
    show_query_builder: function () {
        var builder = new QueryBuilder({columns: this.columns});
        // receive built query back into this.val() when the modal is done
        this.listenTo(builder, 'done', this.val);
    },
});

// Derived from: backgrid-paginator <http://github.com/wyuenho/backgrid-paginator>
// Adjusted to match Beaker's convention for grid pagination controls
var BeakerBackgridPaginator = Backbone.View.extend({
    tagName: 'div',
    className: 'pagination pagination-right',
    template: JST['backgrid-paginator'],
    events: {
        'click a': 'change_page',
    },
    initialize: function () {
        var collection = this.collection;
        this.listenTo(collection, 'add remove reset', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.collection.state));
        return this;
    },
    change_page: function (evt) {
        this.collection.getPage(parseInt($(evt.currentTarget).data('page')));
        evt.preventDefault();
    },
});

window.BeakerGrid = Backbone.View.extend({
    initialize: function (options) {
        var collection = options.collection;
        this.grid = new Backgrid.Grid({
            className: 'backgrid table table-striped table-hover table-condensed',
            collection: collection,
            columns: options.columns,
        });
        this.filter_control = new BeakerBackgridFilter({
            collection: collection,
            columns: options.columns,
        });
        this.top_paginator = new BeakerBackgridPaginator({
            collection: collection,
        });
        this.bottom_paginator = new BeakerBackgridPaginator({
            collection: collection,
        });
        this.render();
        this.listenTo(collection, 'request', this.fetch_started);
        this.listenTo(collection, 'error', this.fetch_error);
        this.listenTo(collection, 'sync', this.fetch_success);
        collection.fetch({reset: true});
    },
    render: function () {
        this.$el.empty()
            .append(this.filter_control.render().el)
            .append(this.top_paginator.render().el)
            .append(this.grid.render().el)
            .append(this.bottom_paginator.render().el);
    },
    fetch_started: function () {
        this.$('.alert').remove();
        if (this.grid.body.$el.width()) {
            // Show semi-transparent overlay over the existing data while the 
            // new data loads.
            var overlay = $('<div class="loading-overlay"><p><i class="icon-spinner icon-spin icon-4x"/></p></div>')
                .width(this.grid.body.$el.width())
                .height(this.grid.body.$el.height())
                .prependTo(this.grid.body.el);
        } else {
            // No body width probably means we are still initializing so the 
            // element has not been inserted to the DOM yet. We can't use an 
            // overlay in this case, we just show the spinner as a block-level 
            // element instead.
            var div = $('<div class="backgrid-initial-loading-indicator"><i class="icon-spinner icon-spin icon-4x"/></div>')
                .insertAfter(this.grid.el);
        }
    },
    fetch_error: function (collection, xhr) {
        this.grid.body.$el.empty();
        // can't put a <div/> inside a <tbody/> so it goes at the bottom instead
        this.$el.append(
            $('<div class="alert alert-error"/>')
            .text('Failed to fetch data while populating grid: ' +
                xhr.statusText + ': ' + xhr.responseText));
    },
    fetch_success: function () {
        this.$('.alert').remove();
        this.$('.loading-overlay').remove();
        this.$('.backgrid-initial-loading-indicator').remove();
    },
});


})();
