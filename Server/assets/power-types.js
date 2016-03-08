
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.

;(function () {

    var PowerTypeListItem = Backbone.View.extend({
        tagName: 'li',
        template: JST['power-type'],
        events: {
            'click .powertype-remove': 'remove_power_type',
        },
        initialize: function(options) {
            this.options = options;
            this.render();
        },
        render: function() {
            var data = _.extend({user_can_edit: this.options['user_can_edit'] || false}, this.model.toJSON());
            this.$el.html(this.template(data));
        },
        remove_power_type: function (evt) {
            $(evt.currentTarget).button('loading');
            this.model.destroy({
                wait: true,
                error: _.bind(this.remove_power_type_error, this)});
            evt.preventDefault();
        },
        remove_power_type_error: function (model, xhr) {
            this.$('button').button('reset');
            // Inconsistent: Using growl here, since appending an error div to the list item will be worse.
            growl_for_xhr(xhr, 'Error deleting power type');
        },
    })

    window.PowerTypesView = Backbone.View.extend({
        initialize: function(options) {
            this.options = options;
            this.render();
            this.listenTo(this.collection, 'add', this.render);
            this.listenTo(this.collection, 'remove', this.render);
        },
        render: function () {
            this.$el.empty();
            this.collection.each(function(power_type) {
                var view = new PowerTypeListItem({model: power_type,
                                                  user_can_edit: this.options['user_can_edit'] || false});
                this.$el.append(view.el);
            }, this);
            return this;
        },
    });

    window.AddPowerTypeForm = Backbone.View.extend({
        template: JST['power-type-add'],
        events: {
            'submit form': 'submit',
        },
        initialize: function() {
            this.render();
        },
        render: function() {
            this.$el.html(
                this.template()
            );
        },
        submit: function(evt) {
            evt.preventDefault();
            var name = this.$('input[type=text][name=power_type_name]').val();
            if (this.collection.find(function(n) { return n.get('name') == name })) {
                this.$('input[type=text][name=power_type_name]').val('');
                return;
            }
            this.$('button').button('loading');
            this.collection.create({name: name}, {
                wait: true,
                success: _.bind(this.success, this),
                error: _.bind(this.error, this)});
        },
        reset_button: function() {
            this.$('button').button('reset');
        },
        success: function(model, xhr) {
            this.reset_button();
            this.$('input[type=text]').val('');
        },
        error: function(model, xhr) {
            this.reset_button();
            this.$el.append(alert_for_xhr(xhr));
        }
    })

})();
