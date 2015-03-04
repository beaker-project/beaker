
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.User = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="mailto:<%- email_address %>" title="<%- display_name %> &lt;<%- email_address %>&gt;"><%- user_name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});

})();
