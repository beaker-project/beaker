
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.CommentsLink = Backbone.View.extend({
    template: JST['comments-link'],
    initialize: function () {
        this.listenTo(this.model.get('comments'), 'reset add remove', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        this.$('.comments-link').beaker_popover({
            model: this.model,
            view_type: CommentsPopover,
        });
        return this;
    },
});

var CommentsPopover = BeakerPopoverView.extend({
    className: 'popover comments-popover',
    render: function () {
        BeakerPopoverView.prototype.render.apply(this);
        new CommentsList({model: this.model}).$el
            .appendTo(this.$('.popover-content'));
        if (this.model.get('can_comment')) {
            new CommentForm({model: this.model}).$el
                .appendTo(this.$('.popover-content'));
        }
    },
});

var CommentsList = Backbone.View.extend({
    template: JST['comments-list'],
    initialize: function (options) {
        this.listenTo(this.model.get('comments'), 'reset add remove', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        if (!this.model.get('comments').isEmpty()) {
            this.$el.addClass('comments');
        }
        return this;
    },
});

var CommentForm = Backbone.View.extend({
    events: {
        'submit form.new-comment': 'add_comment',
    },
    template: JST['comment-form'],
    className: 'comment-form',
    initialize: function (options) {
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        return this;
    },
    add_comment: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        var comment = this.$('textarea[name=comment]').val();
        this.model.get('comments').create({comment: comment}, {
            wait: true,
            success: _.bind(this.save_success, this),
            error: _.bind(this.save_error, this),
        });
    },
    save_success: function (model, xhr, options) {
        this.$('button').button('reset');
        this.$('textarea[name=comment]').val('');
    },
    save_error: function (model, xhr, options) {
        alert_for_xhr(xhr).appendTo(this.$('.sync-status'));
        this.$('button').button('reset');
    },
});

})();
