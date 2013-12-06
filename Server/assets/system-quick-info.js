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
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
});

window.SystemQuickUsage = Backbone.View.extend({
    tagName: 'div',
    className: 'system-quick-usage',
    template: JST['system-quick-usage'],
    initialize: function () {
        this.listenTo(this.model, 'change', this.render);
        this.render();
    },
    render: function () {
        this.$el.html(this.template(this.model.attributes));
    },
});

})();
