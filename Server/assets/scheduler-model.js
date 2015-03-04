
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.Job = Backbone.Model.extend({
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- id %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});

window.RecipeSet = Backbone.Model.extend({
    parse: function (data) {
        data['job'] = !_.isEmpty(data['job']) ? new Job(data['job']) : null;
        return data;
    },
    _toHTML_template: _.template('<a href="<%- beaker_url_prefix %>jobs/<%- job.get("id") %>"><%- t_id %></a>'),
    toHTML: function () {
        return this._toHTML_template(this.attributes);
    },
});


})();
