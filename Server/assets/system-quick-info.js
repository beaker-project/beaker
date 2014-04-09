
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

window.SystemQuickInfo = Backbone.View.extend({
    initialize: function () {
        this.render();
    },
    render: function () {
        this.$el.addClass('row-fluid');
        new SystemQuickDescription({model: this.model}).$el
            .addClass('span4').appendTo(this.$el);
        new SystemQuickHealth({model: this.model}).$el
            .addClass('span4').appendTo(this.$el);
        new SystemQuickUsage({model: this.model}).$el
            .addClass('span4').appendTo(this.$el);
    },
});

window.SystemQuickDescription = Backbone.View.extend({
    tagName: 'div',
    className: 'system-quick-description',
    template: JST['system-quick-description'],
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
});

window.SystemQuickHealth = Backbone.View.extend({
    tagName: 'div',
    className: 'system-quick-health',
    template: JST['system-quick-health'],
    events: {
        'click .report-problem': 'report_problem',
    },
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    report_problem: function (evt) {
        new SystemReportProblemModal({model: this.model});
    },
});

window.SystemQuickUsage = Backbone.View.extend({
    tagName: 'div',
    className: 'system-quick-usage',
    template: JST['system-quick-usage'],
    events: {
        'click .take': 'take',
        'click .return': 'return',
        'click .borrow': 'borrow',
        'click .request-loan': 'request_loan',
    },
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    error: function (model, xhr) {
        // XXX this isn't great... better to use notification float thingies
        this.$el.append(
            $('<div class="alert alert-error"/>')
            .text(xhr.statusText + ': ' + xhr.responseText));
    },
    take: function (evt) {
        $(evt.currentTarget).prop('disabled', true)
            .html('<i class="icon-spinner icon-spin"></i> Taking&hellip;');
        this.model.take({error: _.bind(this.error, this)});
    },
    'return': function (evt) {
        $(evt.currentTarget).prop('disabled', true)
            .html('<i class="icon-spinner icon-spin"></i> Returning&hellip;');
        this.model.return({error: _.bind(this.error, this)});
    },
    borrow: function (evt) {
        $(evt.currentTarget).prop('disabled', true)
            .html('<i class="icon-spinner icon-spin"></i> Borrowing&hellip;');
        this.model.borrow({error: _.bind(this.error, this)});
    },
    request_loan: function (evt) {
        new SystemLoanRequestModal({model: this.model});
    },
});

})();
