;(function () {

window.SystemActivityView = Backbone.View.extend({
    initialize: function () {
        this.grid = new Backgrid.Grid({
            className: 'backgrid table table-striped table-hover table-condensed',
            collection: this.model.activity,
            columns: [
                {name: 'user', label: 'User', cell: BackgridUserCell, editable: false},
                {name: 'service', label: 'Service', cell: 'string', editable: false},
                {name: 'created', label: 'Created', cell: BackgridDateTimeCell, editable: false},
                {name: 'field_name', label: 'Field Name', cell: 'string', editable: false},
                {name: 'action', label: 'Action', cell: 'string', editable: false},
                {name: 'old_value', label: 'Old Value', cell: 'string', editable: false},
                {name: 'new_value', label: 'New Value', cell: 'string', editable: false},
            ],
        });
        this.paginator = new BeakerBackgridPaginator({
            collection: this.model.activity,
        });
        this.render();
    },
    render: function () {
        var $el = this.$el, grid = this.grid, paginator = this.paginator;
        this.model.activity.fetch({
            reset: true,
            success: function () {
                grid.render();
                $el.empty().append(grid.el).append(paginator.el);
            },
            error: function (collection, xhr) {
                $el.empty().append(
                    $('<div class="alert alert-error"/>')
                    .text('Failed to fetch activity: ' +
                        xhr.statusText + ': ' + xhr.responseText));
            },
        });
    },
});

})();
