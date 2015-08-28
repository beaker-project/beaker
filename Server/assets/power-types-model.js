// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

    window.PowerType = Backbone.Model.extend({
    });

    window.PowerTypes = Backbone.Collection.extend({
        model: PowerType,
        initialize: function (attributes, options) {
            this.url = options.url;
            this.comparator = 'name';
        },
    });

})();
