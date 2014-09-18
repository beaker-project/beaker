
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

/**
 * Distro-related models for client-side Backbone widgets.
 */

window.Distro = Backbone.Model.extend({});

window.DistroTree = Backbone.Model.extend({
    parse: function (data) {
        data['distro'] = !_.isEmpty(data['distro']) ? new Distro(data['distro']) : null;
        return data;
    },
});

})();
