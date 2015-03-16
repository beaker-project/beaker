
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.AccessPolicyRule = Backbone.Model.extend({
    // ensure the 'everybody' attribute is filled in
    initialize: function (attributes, options) {
        if (!_.has(attributes, 'everybody')) {
            this.set('everybody', (attributes['user'] == null &&
                    attributes['group'] == null));
        }
    },
});

window.AccessPolicyRules = Backbone.Collection.extend({
    model: AccessPolicyRule,
});

})();
