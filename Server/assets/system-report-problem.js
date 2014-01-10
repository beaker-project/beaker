;(function () {

window.SystemReportProblemModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-report-problem'],
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
        this.$('button').prop('disabled', true);
        this.$('button[type=submit]').html(
                '<i class="icon-spinner icon-spin"></i> Sending&hellip;');
        this.model.report_problem(
            this.$('[name=message]').val(),
            {success: _.bind(this.save_success, this),
             error: _.bind(this.save_error, this)});
    },
    save_success: function () {
        this.$el.modal('hide');
        $.bootstrapGrowl('<h4>Report sent</h4> Your problem report has been ' +
                'forwarded to the system owner.',
                {type: 'success'});
    },
    save_error: function (model, xhr) {
        this.$('.modal-footer').prepend(
            $('<div class="alert alert-error"/>')
            .text(xhr.statusText + ': ' + xhr.responseText));
    },
});

})();
