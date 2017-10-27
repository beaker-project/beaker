
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipePageHeaderView = Backbone.View.extend({
    template: JST['recipe-header'],
    events: {
        'click .edit': 'edit',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:is_deleted change:can_edit', this.render);
        // This view also updates the page title based on these attributes...
        this.listenTo(this.model, 'change:whiteboard change:status change:result', this.render);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var title = this.model.get('t_id');
        if (this.model.get('whiteboard'))
            title += ' \u00b7 ' + truncated_whiteboard(this.model.get('whiteboard'));
        title += ' \u00b7 ' + this.model.get('status') + '/' + this.model.get('result');
        document.title = title;
    },
    edit: function () {
        new RecipeEditModal({model: this.model});
    },
});

var RecipeEditModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['recipe-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=whiteboard]').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('[name=whiteboard]').val(this.model.get('whiteboard'));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var attributes = {
            whiteboard: this.$('[name=whiteboard]').val(),
        };
        this.model.save(attributes, {patch: true, wait: true})
            .done(_.bind(this.save_success, this))
            .fail(_.bind(this.save_error, this));
    },
    save_success: function (response, status, xhr) {
        this.$el.modal('hide');
    },
    save_error: function (xhr) {
        alert_for_xhr(xhr).appendTo(this.$('.sync-status'));
        this.$('.modal-footer button').button('reset');
    },
});

})();
