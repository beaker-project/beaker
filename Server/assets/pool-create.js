
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.PoolCreateModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['pool-create'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input[name="name"]').focus();
    },
    render: function () {
        this.$el.html(this.template({}));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        var new_pool = new this.collection.model(
                {name: this.$('input[name=name]').val()},
                {collection: this.collection});
        new_pool.save()
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        window.location = xhr.getResponseHeader('Location');
    },
    save_error: function (xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

})();
