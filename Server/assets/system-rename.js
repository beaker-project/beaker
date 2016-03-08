
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

var SystemRenameModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-rename'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input').first().focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('input[name=fqdn]').val(this.model.get('fqdn'));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        this.model.save({fqdn: this.$('input[name=fqdn]').val()},
            {patch: true, wait: true})
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        if (xhr.getResponseHeader('Location'))
            window.location = xhr.getResponseHeader('Location');
        else
            this.$el.modal('hide');
    },
    save_error: function (xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

window.SystemRenameButton = Backbone.View.extend({
    tagName: 'button',
    attributes: {type: 'button'},
    className: 'btn',
    events: {
        'click': 'click',
    },
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.html('<i class="fa fa-pencil-square-o"></i> Rename')
    },
    click: function () {
        new SystemRenameModal({model: this.model});
    },
});

})();
