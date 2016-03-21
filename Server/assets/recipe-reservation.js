
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.RecipeReservationView = Backbone.View.extend({
    className: 'tab-pane recipe-reservation',
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        var $el = this.$el;
        $el.empty();
        var recipe_status = this.model.get('status');
        if (recipe_status == 'Completed' ||
            recipe_status == 'Cancelled' ||
            recipe_status == 'Aborted'
        ) {
            $el.append(new RecipeCompletedReservation({
                model: this.model}).el);
        } else if (recipe_status == 'Reserved') {
            $el.append(new RecipeRunningReservation({
                model: this.model}).el);
        } else {
            $el.append(new RecipePendingReservation({
                model: this.model}).el);
        }
    },
});

var RecipeCompletedReservation = Backbone.View.extend({
    template: JST['recipe-completed-reservation'],
    initialize: function () {
        this.render();
    },
    render: function () {
        var all_recipes = this.model.get('recipeset')
           .get('job').all_recipes();
        var running_recipes = _.filter(all_recipes,
            function(recipe){ return (
                recipe.get('status') != 'Completed' &&
                recipe.get('status') != 'Cancelled' &&
                recipe.get('status') != 'Aborted' ); });
        this.$el.html(this.template(_.extend({running_recipes: running_recipes},
            this.model.attributes)));
    }
});

var RecipeRunningReservation = Backbone.View.extend({
    template: JST['recipe-running-reservation'],
    events: {
        'click .extend-reservation': 'extend_reservation',
        'click .return-reservation': 'return_reservation',
    },
    extend_reservation: function () {
        new RecipeExtendReservation({model: this.model});
    },
    return_reservation: function (evt) {
        var model = this.model, $rel_btn = $(evt.currentTarget);
        $rel_btn.button('loading');
        bootbox.confirm_as_promise('<p>Are you sure you want to return this reservation?</p>')
            .fail(function () { $rel_btn.button('reset'); })
            .then(function () { return model.update_reservation(0); })
            .fail(_.bind(this.return_error, this));
    },
    return_error: function(xhr) {
        if (!_.isEmpty(xhr)) {
            growl_for_xhr(xhr, 'Failed to return');
            this.$('.return-reservation').button('reset');
        }
    },
    initialize: function (options) {
        this.listenTo(this.model, 'change:time_remaining_seconds', this.render);
        this.render();
    },
    clearTimer: function () {
        window.clearInterval(this.timer);
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    }
});

var RecipeExtendReservation = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['recipe-extend-reservation'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        if(this.model.get('time_remaining_seconds') > 0) {
            this.$('[name=kill_time]').val(this.model.get('time_remaining_seconds'));
        }
        this.$('[name=kill_time]').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var kill_time = this.$('[name=kill_time]').val();
        this.model.update_reservation(kill_time)
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

var RecipePendingReservation = Backbone.View.extend({
    template: JST['recipe-pending-reservation'],
    events: {
        'click .edit': 'edit',
    },
    edit: function () {
        new EditRecipeReservationModal({model: this.model});
    },
    initialize: function (options) {
        this.listenTo(this.model.get('reservation_request'), 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    }
});

var EditRecipeReservationModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['recipe-reservation-edit'],
    events: {
        'click .btn-group .btn': 'toggle_reservation',
        'submit form': 'submit',
        'hidden': 'remove',
    },
    toggle_reservation: function (evt) {
        if ($(evt.currentTarget).data('reserve')) {
            this.$('.recipe-reservation-duration').show()
                 .find(':input').prop('disabled', false);
        } else {
            this.$('.recipe-reservation-duration').hide()
                 .find(':input').prop('disabled', true);
        }
    },
    initialize: function () {
        this.render();
        this.$el.modal();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
        var model = this.model;
        var reservation_request = this.model.get('reservation_request');
        if (reservation_request.get('reserve')) {
            this.$('button[data-reserve="true"]').addClass('active');
            this.$('input[name="duration"]').val(reservation_request.get('duration'));
        } else {
            this.$('button[data-reserve="false"]').addClass('active');
            this.$('.recipe-reservation-duration').hide()
                 .find(':input').prop('disabled', true);
        }
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('.modal-footer button').button('loading');
        var reserve = this.$('button.active').data('reserve');
        var model = this.model;
        var attributes = {};
        if (reserve) {
            attributes.reserve = true;
            attributes.duration = parseInt(this.$('[name=duration]').val());
        } else {
            attributes.reserve = false;
        }
        model.get('reservation_request').save(attributes, {patch: true, wait: true})
            .then(function() {return model.fetch();})
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
