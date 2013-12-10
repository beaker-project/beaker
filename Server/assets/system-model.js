;(function () {

/**
 * System-related models for client-side Backbone widgets.
 */

// XXX this needs to be moved somewhere better
window.User = Backbone.Model.extend({});

window.Reservation = Backbone.Model.extend({
    parse: function (data) {
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        return data;
    },
});

window.System = Backbone.Model.extend({
    parse: function (data) {
        data['owner'] = !_.isEmpty(data['owner']) ? new User(data['owner']) : null;
        data['user'] = !_.isEmpty(data['user']) ? new User(data['user']) : null;
        data['loaned'] = !_.isEmpty(data['loaned']) ? new User(data['loaned']) : null;
        data['current_reservation'] = (!_.isEmpty(data['current_reservation']) ?
                new Reservation(data['current_reservation'], {parse: true}) : null);
        data['previous_reservation'] = (!_.isEmpty(data['previous_reservation']) ?
                new Reservation(data['previous_reservation'], {parse: true}) : null);
        return data;
    },
    add_cc: function (cc, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'cc/' + encodeURIComponent(cc),
            type: 'PUT',
            dataType: 'json',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
                // response body should have the new list of CC
                model.set(data);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
    remove_cc: function (cc, options) {
        var model = this;
        options = options || {};
        $.ajax({
            url: this.url + 'cc/' + encodeURIComponent(cc),
            type: 'DELETE',
            dataType: 'json',
            success: function (data, status, jqxhr) {
                if (options.success)
                    options.success(model, data, options);
                // response body should have the new list of CC
                model.set(data);
            },
            error: function (jqxhr, status, error) {
                if (options.error)
                    options.error(model, jqxhr, options);
            },
        });
    },
});

})();
