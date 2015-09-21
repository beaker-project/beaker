
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * Distro-related models for client-side Backbone widgets.
 */

window.Distro = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>distros/view?id=<%- id %>"><%- name %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});

window.DistroTree = Backbone.Model.extend({
    parse: function (data) {
        data['distro'] = !_.isEmpty(data['distro']) ? new Distro(data['distro']) : null;
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>distrotrees/<%- id %>"><%- distro.get("name") %> <%- variant %> <%- arch %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
    _toString_template: _.template('<%- distro.get("name") %> <%- variant %> <%- arch %>'),
    toString: function() {
        return this._toString_template(this.attributes);
    }
});

})();
