
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemLoanView = Backbone.View.extend({
    template: JST['system-loan'],
    events: {
        'click .borrow': 'borrow',
        'click .lend': 'lend',
        'click .return': 'return',
        'click .request-loan': 'request_loan',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:current_loan', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    borrow: function () {
        this.$('.borrow').button('loading');
        this.model.borrow({error: _.bind(this.error, this)});
    },
    lend: function () {
        new SystemLendModal({model: this.model});
    },
    'return': function () {
        this.$('.return').button('loading');
        this.model.return_loan({error: _.bind(this.error, this)});
    },
    request_loan: function () {
        new SystemLoanRequestModal({model: this.model});
    },
    error: function (model, xhr) {
        this.$el.append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

var SystemLendModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-lend'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input[name="recipient"]').beaker_typeahead('user-name').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        this.model.lend(
            this.$('input[name=recipient]').val(),
            this.$('textarea[name=comment]').val(),
            {success: _.bind(this.save_success, this),
             error: _.bind(this.save_error, this)});
        evt.preventDefault();
    },
    save_success: function () {
        this.$el.modal('hide');
    },
    save_error: function (model, xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

window.SystemLoanRequestModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-loan-request'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('[name=message]').focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        evt.preventDefault();
        this.$('.sync-status').empty();
        this.$('button').button('loading');
        this.model.request_loan(
            this.$('[name=message]').val(),
            {success: _.bind(this.save_success, this),
             error: _.bind(this.save_error, this)});
    },
    save_success: function () {
        this.$el.modal('hide');
        $.bootstrapGrowl('<h4>Request sent</h4> Your loan request has been ' +
                'forwarded to the system owner.',
                {type: 'success'});
    },
    save_error: function (model, xhr) {
        this.$('.sync-status').append(alert_for_xhr(xhr));
        this.$('button').button('reset');
    },
});

})();
