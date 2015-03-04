
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

// Note that we also have SystemsActivityView (plural) which shows all system 
// activity records.
window.SystemActivityView = BeakerGrid.extend({
    initialize: function (options) {
        options.collection = this.model.activity;
        options.columns = [
            {name: 'user', label: 'User', cell: BackgridUserCell, editable: false},
            {name: 'service', label: 'Service', cell: 'string', editable: false},
            {name: 'created', label: 'Created', cell: BackgridDateTimeCell, editable: false},
            {name: 'field_name', label: 'Field Name', cell: 'string', editable: false},
            {name: 'action', label: 'Action', cell: 'string', editable: false},
            {name: 'old_value', label: 'Old Value', cell: 'string', editable: false},
            {name: 'new_value', label: 'New Value', cell: 'string', editable: false},
        ];
        options.name = 'system activity';
        BeakerGrid.prototype.initialize.apply(this, arguments);
    },
});

})();
