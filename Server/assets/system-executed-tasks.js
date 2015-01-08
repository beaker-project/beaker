
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemExecutedTasksView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model.executed_tasks;
        options.columns = [
            {name: 't_id', label: 'Run ID', cell: BackgridRecipeTaskIdCell, editable: false},
            {name: 'name', label: 'Task', cell: BackgridTaskCell, editable: false},
            {name: 'distro_tree', label: 'Distro Tree', cell: BackgridDistroTreeCell, editable: false},
            {name: 'start_time', label: 'Start Time', cell: BackgridDateTimeCell, editable: false},
            {name: 'finish_time', label: 'Finish Time', cell: BackgridDateTimeCell, editable: false},
            {name: 'status', label: 'Status', cell: BackgridStatusCell, editable: false},
            {name: 'result', label: 'Result', cell: BackgridResultCell, editable: false},
        ];
        options.name = 'executed tasks';
        options.query_builder_columns = [
            {name: 'id', label: 'Run ID'},
            {name: 'name', label: 'Task'},
            {name: 'distro_tree.distro.name', label: 'Distro/Name'},
            {name: 'distro_tree.variant', label: 'Distro Tree/Variant'},
            {name: 'distro_tree.arch', label: 'Distro Tree/Arch'},
            {name: 'start_time', label: 'Start Time'},
            {name: 'finish_time', label: 'Finish Time'},
            {name: 'status', label: 'Status'},
            {name: 'result', label: 'Result'},
        ];
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

})();
