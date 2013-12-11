;(function () {

window.SystemHardwareDetailsView = Backbone.View.extend({
    template: JST['system-hardware-details'],
    events: {
        'click .edit': 'edit',
    },
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    edit: function () {
        new SystemHardwareDetailsEdit({model: this.model});
    },
});

var SystemHardwareDetailsEdit = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-hardware-details-edit'],
    events: {
        'submit form': 'submit',
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        var model = this.model;
        this.$('input, select').each(function (i, elem) {
            $(elem).val(model.get(elem.name));
        });
        this.$('input, select').first().focus();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
    submit: function (evt) {
        this.$('button').prop('disabled', true);
        this.$('button[type=submit]').html(
                '<i class="icon-spinner icon-spin"></i> Saving&hellip;');
        var attributes = _.object(_.map(this.$('input, select'),
                function (elem) { return [elem.name, $(elem).val()]; }));
        this.model.save(
            attributes,
            {patch: true, wait: true,
             success: _.bind(this.save_success, this),
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
