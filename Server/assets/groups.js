
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var GroupNameCell = Backgrid.StringCell.extend({
    className: 'group-name-cell',
    render: function () {
        this.$el.empty();
        this.$el.html(this.model.toHTML());
        return this;
    },
});

window.GroupsView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model;
        options.name = 'groups';
        options.columns = [
            {name: 'group_name', label: 'Group Name', cell: GroupNameCell, editable: false},
            {name: 'display_name', label: 'Display Name', cell: 'string', editable: false},
            {name: 'created', label: 'Created', cell: BackgridDateTimeCell, editable: false},
        ];
        options.query_builder_columns = options.columns.concat([
            {name: 'member.user_name', label: 'Member/Username'},
            {name: 'member.display_name', label: 'Member/Display Name'},
            {name: 'member.email_address', label: 'Member/Email Address'},
            {name: 'owner.user_name', label: 'Owner/Username'},
            {name: 'owner.display_name', label: 'Owner/Display Name'},
            {name: 'owner.email_address', label: 'Owner/Email Address'},
        ]);
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

})();
