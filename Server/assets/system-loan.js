;(function () {

window.SystemLoanView = Backbone.View.extend({
    template: JST['system-loan'],
    events: {
        'click .borrow': 'borrow',
        'click .lend': 'lend',
        'click .return': 'return',
    },
    initialize: function () {
        this.listenTo(this.model, 'change:current_loan', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    borrow: function () {
        this.$('button').prop('disabled', true);
        this.$('.sync-status').html(
                '<i class="icon-spinner icon-spin"></i> Borrowing&hellip;');
        this.model.borrow({error: _.bind(this.error, this)});
    },
    lend: function () {
        new SystemLendModal({model: this.model});
    },
    'return': function () {
        this.$('button').prop('disabled', true);
        this.$('.sync-status').html(
                '<i class="icon-spinner icon-spin"></i> Returning&hellip;');
        this.model.return_loan({error: _.bind(this.error, this)});
    },
    error: function (model, xhr) {
        this.$el.append(
            $('<div class="alert alert-error"/>')
            .text(xhr.statusText + ': ' + xhr.responseText));
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
        this.$('button').prop('disabled', true);
        this.$('button[type=submit]').html(
                '<i class="icon-spinner icon-spin"></i> Saving&hellip;');
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
        this.$('.modal-footer').prepend(
            $('<div class="alert alert-error"/>')
            .text(xhr.statusText + ': ' + xhr.responseText));
    },
});

})();
