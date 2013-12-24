;(function () {

window.SystemAddModal = Backbone.View.extend({
    tagName: 'div',
    className: 'modal',
    template: JST['system-add'],
    events: {
        'hidden': 'remove',
    },
    initialize: function () {
        this.render();
        this.$el.modal();
        this.$('input[name="fqdn"]').focus();
    },
    render: function () {
        this.$el.html(this.template({}));
    },
});

})();
