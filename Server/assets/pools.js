
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var PoolNameCell = Backgrid.StringCell.extend({
    className: 'pool-name-cell',
    render: function () {
        this.$el.empty();
        this.$el.html(this.model.toHTML());
        return this;
    },
});

var PoolOwnerCell = Backgrid.Cell.extend({
    className: 'pool-owner-cell',
    render: function () {
        this.$el.empty();
        var owner = this.model.get(this.column.get('name'));
        if (!_.isEmpty(owner)) {
            this.$el.html(owner.toHTML());
        }
        return this;
    },
});

window.PoolsView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model;
        options.name = 'pools';
        options.columns = [
            {name: 'name', label: 'Name', cell: PoolNameCell, editable: false},
            {name: 'owner', label: 'Owner', cell: PoolOwnerCell, editable: false, sortable: false},
            {name: 'description', label: 'Description', cell: BackgridTruncatedMarkdownCell, editable: false},
        ];
        options.query_builder_columns = [
            {name: 'name', label: 'Name'},
            {name: 'owner.user_name', label: 'Owner/Username'},
            {name: 'owner.group_name', label: 'Owner/Group Name'},
        ];
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

})();
