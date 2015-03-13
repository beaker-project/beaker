
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var ActivityObjectCell = Backgrid.Cell.extend({
    className: 'activity-object-cell',
    render: function () {
        this.$el.empty();
        var object = this.model.get(this.column.get('name'));
        this.$el.html(_.result(object, 'toHTML', ''));
        return this;
    },
});

// We have ActivityView, which shows activity of all types. And we have 
// specialised views for showing each specific activity type. The specialised 
// views are basically identical, except:
// * they use the specific column header (Distro, System, etc) instead of Object
// * their query builder allows searching on attributes of the specific type (Distro/Name, etc)

window.ActivityView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model;
        options.name = 'activity';
        var object_column_label = options.object_column_label || 'Object';
        options.columns = [
            {name: 'user', label: 'User', cell: BackgridUserCell, editable: false, sortable: false},
            {name: 'service', label: 'Via', cell: 'string', editable: false},
            {name: 'created', label: 'Created', cell: BackgridDateTimeCell, editable: false},
            {name: 'object', label: object_column_label, cell: ActivityObjectCell, editable: false, sortable: false},
            {name: 'field_name', label: 'Property', cell: 'string', editable: false},
            {name: 'action', label: 'Action', cell: 'string', editable: false},
            {name: 'old_value', label: 'Old Value', cell: 'string', editable: false},
            {name: 'new_value', label: 'New Value', cell: 'string', editable: false},
        ];
        options.query_builder_columns = (options.object_query_builder_columns || []).concat([
            {name: 'field_name', label: 'Property'},
            {name: 'action', label: 'Action'},
            {name: 'old_value', label: 'Old Value'},
            {name: 'new_value', label: 'New Value'},
            {name: 'service', label: 'Via'},
            {name: 'created', label: 'Created', cell: BackgridDateTimeCell},
        ]);
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

window.DistroActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'Distro';
        options.object_query_builder_columns = [
            {name: 'distro.name', label: 'Distro/Name'},
        ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

window.DistroTreeActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'Distro Tree';
        options.object_query_builder_columns = [
            {name: 'distro_tree.distro.name', label: 'Distro/Name'},
            {name: 'distro_tree.variant', label: 'Distro Tree/Variant'},
            {name: 'distro_tree.arch', label: 'Distro Tree/Arch'},
        ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

window.GroupActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'Group';
        options.object_query_builder_columns = [
            {name: 'group.group_name', label: 'Group/Name'},
        ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

window.LabControllerActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'Lab Controller';
        options.object_query_builder_columns = [
            {name: 'lab_controller.fqdn', label: 'Lab Controller/FQDN'},
        ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

// Note that we also have SystemActivityView which is on the system page, for 
// showing a single system's activity records! This one shows all system 
// activity records.
window.SystemsActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'System';
        options.object_query_builder_columns = [
            {name: 'system.fqdn', label: 'System/FQDN'},
        ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

window.SystemPoolActivityView = ActivityView.extend({
    initialize: function (options) {
        options.object_column_label = 'System Pool';
        options.object_query_builder_columns = [
                {name: 'pool.name', label: 'System Pool/Name'},
                {name:'pool.owner.user_name', label: 'Owner/Username'},
                {name:'pool.owner.group_name', label: 'Owner/Group Name'},
                ];
        ActivityView.prototype.initialize.apply(this, arguments);
    },
});

})();
