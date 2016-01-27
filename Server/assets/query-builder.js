
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

/* Modal for building query strings suitable for Backgrid filtering.
 * Presents a UI similar to the old searchbar and converts the query into the 
 * Lucene-compatible syntax used for new Backgrids (implemented in
 * @json_collection). */

;(function () {

var QueryBuilderRow = Backbone.View.extend({
    tagName: 'div',
    className: 'query-builder-row',
    template: JST['query-builder-row'],
    events: {
        'keypress [name=field]': 'field_changed',
        'change [name=field]': 'field_changed',
        'keypress [name=operator]': 'operator_changed',
        'change [name=operator]': 'operator_changed',
    },
    initialize: function (options) {
        this.columns = options.columns;
        this.render();
    },
    render: function () {
        this.$el.html(this.template({columns: this.columns}));
    },
    field_changed: function (evt) {
        var selected_field = this.$('[name=field]').val();
        var column = _.find(this.columns,
                function (column) { return column.name == selected_field; });
        // Disable operators that don't make sense for this field.
        var disabled_operators = [];
        if (_.contains([Backgrid.NumberCell, BackgridDateTimeCell], column.cell)) {
            disabled_operators.push('contains', '!contains');
        }
        if (_.contains([Backgrid.BooleanCell, BackgridBooleanYesCell], column.cell)) {
            disabled_operators.push('>', '>=', '<', '<=', 'contains', '!contains');
        }
        this.$('[name=operator] option').prop('disabled',
                function () { return _.contains(disabled_operators, this.value); });
        // Use datepicker if it's a date field.
        if (column.cell == BackgridDateTimeCell)
            this.$('[name=value]').datepicker({autoclose: true, format: 'yyyy-mm-dd'});
        else
            this.$('[name=value]').datepicker('remove');
        // Constrain value to "true"/"false" if it's a boolean field.
        // (Better would be to show a <select/> but that means restructuring 
        // this entire widget...)
        if (_.contains([Backgrid.BooleanCell, BackgridBooleanYesCell], column.cell)) {
            this.$('[name=value]').attr('pattern', 'true|false')
                                  .attr('required', true)
                                  .attr('title', 'Boolean value true or false');
        } else {
            this.$('[name=value]').removeAttr('pattern required title');
        }
    },
    operator_changed: function (evt) {
        var selected_operator = this.$('[name=operator]').val();
        this.$('[name=value]').prop('disabled',
                selected_operator == 'null' || selected_operator == '!null');
    },
    to_lucene_term: function () {
        var field = this.$('[name=field]').val();
        var operator = this.$('[name=operator]').val();
        var value = this.$('[name=value]').val();
        var pieces = [];
        if (operator == '!=' || operator == '!contains' || operator == 'null')
            pieces.push('-');
        pieces.push(field);
        pieces.push(':');
        if (operator == '>') {
            pieces.push('{');
            pieces.push(value);
            pieces.push(' TO *]');
        } else if (operator == '>=') {
            pieces.push('[');
            pieces.push(value);
            pieces.push(' TO *]');
        } else if (operator == '<') {
            pieces.push('[* TO ');
            pieces.push(value);
            pieces.push('}');
        } else if (operator == '<=') {
            pieces.push('[* TO ');
            pieces.push(value);
            pieces.push(']');
        } else if (operator == 'contains' || operator == '!contains') {
            pieces.push('*');
            pieces.push(value);
            pieces.push('*');
        } else if (operator == 'null' || operator == '!null') {
            pieces.push('*');
        } else {
            if (!value)
                pieces.push('""');
            else if (/[\[\]\s]/.test(value))
                pieces.push('"' + value + '"'); // XXX should escape "
            else
                pieces.push(value);
        }
        return pieces.join('');
    },
});

window.QueryBuilder = Backbone.View.extend({
    tagName: 'div',
    className: 'modal query-builder',
    template: JST['query-builder'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
        'keypress input, select': 'build_query_debounced',
        'change input, select': 'build_query',
        'input input': 'build_query_debounced',
        'click .add': 'add_row',
        'click .remove': 'remove_row',
    },
    initialize: function (options) {
        this.columns = options.columns;
        this.rows = [new QueryBuilderRow({columns: this.columns})];
        this.grid_name = options.grid_name;
        this.render();
        this.build_query();
        // backdrop:'static' prevents the modal being closed when clicking 
        // outside it, which would be really annoying while trying to build 
        // a query.
        this.$el.modal({backdrop: 'static'});
        this.rows[0].$('select').first().focus();
    },
    render: function () {
        this.$el.html(this.template({grid_name: this.grid_name}));
        this.$('.query-builder-rows').append(_.pluck(this.rows, 'el'));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.build_query();
        this.trigger('done', this.query);
        this.$el.modal('hide');
    },
    build_query: function (evt) {
        var terms = _.invoke(this.rows, 'to_lucene_term');
        this.query = terms.join(' ');
        this.$('.query').text(this.query);
    },
    add_row: function (evt) {
        evt.preventDefault();
        var row = new QueryBuilderRow({columns: this.columns});
        this.rows.push(row);
        this.build_query();
        this.$('.query-builder-rows').append(row.el);
        row.$('select').first().focus();
    },
    remove_row: function (evt) {
        evt.preventDefault();
        var row = _.find(this.rows,
                function (row) { return $.contains(row.el, evt.currentTarget); });
        if (row === undefined)
            return;
        row.$el.remove();
        var row_index = _.indexOf(this.rows, row);
        this.rows.splice(row_index, 1); // delete it
        this.build_query();
    },
});
QueryBuilder.prototype.build_query_debounced = _.debounce(
        QueryBuilder.prototype.build_query,
        50 /* ms */);

})();
