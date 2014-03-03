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
